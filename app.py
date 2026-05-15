from math import log
import os
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
import joblib
import pandas as pd
import json
from functools import wraps
from flask import session
import mysql.connector
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from collections import defaultdict
from utils.preprocessing import preprocess_pipeline
from utils.tfidf import build_tfidf, build_tfidf_single, compute_tf, compute_tfidf
from utils.naive_bayes import ManualNaiveBayes
from sklearn.model_selection import train_test_split
from sklearn.metrics import (
    accuracy_score, precision_score,
    recall_score, f1_score, confusion_matrix
)
try:
    from imblearn.over_sampling import SMOTE
    SMOTE_AVAILABLE = True
except ImportError:
    SMOTE_AVAILABLE = False


app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRET', 'supersecretkey')

DB_CONFIG = {
    'host'    : os.environ.get('DB_HOST', 'localhost'),
    'user'    : os.environ.get('DB_USER', 'root'),
    'password': os.environ.get('DB_PASS', ''),
    'database': os.environ.get('DB_NAME', 'db_sentimen')
}

MODEL_DIR = 'model'
os.makedirs(MODEL_DIR, exist_ok=True)


# ── Helpers ────────────────────────────────────────────────────────────
def get_db_conn():
    return mysql.connector.connect(**DB_CONFIG)

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            flash("Silakan login terlebih dahulu.", "warning")
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            flash("Silakan login terlebih dahulu.", "warning")
            return redirect(url_for('login'))
        if session.get('role', '').lower() != 'admin':
            flash('Anda tidak memiliki akses ke halaman ini.', 'danger')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated


# ── Dashboard ──────────────────────────────────────────────────────────
@app.route('/')
@app.route('/dashboard')
@login_required
def dashboard():
    conn = get_db_conn()
    cur  = conn.cursor(dictionary=True)

    totals           = {'total': 0, 'train': 0, 'test': 0}
    latest_accuracy  = None
    sentiment_counts = {'Positif': 0, 'Negatif': 0}
    train_counts     = {'Positif': 0, 'Negatif': 0}
    test_counts      = {'Positif': 0, 'Negatif': 0}
    weekly_trend     = []
    wordcloud_pos    = []
    wordcloud_neg    = []

    try:
        cur.execute('SELECT COUNT(*) as cnt FROM data_sentimen')
        totals['total'] = cur.fetchone()['cnt']
    except: pass

    try:
        cur.execute('SELECT COUNT(*) as cnt FROM data_training')
        totals['train'] = cur.fetchone()['cnt']
    except: pass

    try:
        cur.execute('SELECT COUNT(*) as cnt FROM data_testing')
        totals['test'] = cur.fetchone()['cnt']
    except: pass

    try:
        cur.execute("SELECT accuracy FROM hasil_analisis ORDER BY created_at DESC LIMIT 1")
        row = cur.fetchone()
        if row:
            latest_accuracy = round(row['accuracy'] * 100, 2)
    except: pass

    try:
        cur.execute("SELECT Label, COUNT(*) as cnt FROM data_sentimen GROUP BY Label")
        for row in cur.fetchall():
            sentiment_counts[row['Label']] = row['cnt']
    except: pass

    try:
        cur.execute("SELECT Label, COUNT(*) as cnt FROM data_training GROUP BY Label")
        for row in cur.fetchall():
            train_counts[row['Label']] = row['cnt']
    except: pass

    try:
        cur.execute("SELECT Label, COUNT(*) as cnt FROM data_testing GROUP BY Label")
        for row in cur.fetchall():
            test_counts[row['Label']] = row['cnt']
    except: pass

   # ── Trend Perminggu ────────────────────────────────────────────────
    try:
        cur.execute("SELECT createTimeISO, Label FROM data_sentimen WHERE createTimeISO IS NOT NULL AND createTimeISO != ''")
        rows = cur.fetchall()

        from datetime import datetime, timezone
        import calendar

        NAMA_BULAN = ['', 'Jan', 'Feb', 'Mar', 'Apr', 'Mei', 'Jun',
                      'Jul', 'Agu', 'Sep', 'Okt', 'Nov', 'Des']

        def parse_tanggal(s):
            """Parsing dua format: ISO dan Twitter."""
            s = str(s).strip()
            for fmt in (
                '%Y-%m-%dT%H:%M:%S.%fZ',
                '%Y-%m-%dT%H:%M:%SZ',
                '%Y-%m-%dT%H:%M:%S.%f',
                '%Y-%m-%dT%H:%M:%S',
                '%a %b %d %H:%M:%S +0000 %Y',   # Twitter: Tue Dec 09 23:58:08 +0000 2025
            ):
                try:
                    return datetime.strptime(s, fmt)
                except ValueError:
                    continue
            return None

        week_map = defaultdict(lambda: {'Positif': 0, 'Negatif': 0, 'label': '', '_year': 0, '_week': 0})

        for row in rows:
            dt = parse_tanggal(row['createTimeISO'])
            if dt is None:
                continue
            year, week_num, _ = dt.isocalendar()
            # Cari Senin awal minggu itu
            monday = dt - __import__('datetime').timedelta(days=dt.weekday())
            # tgl_mulai = f"{monday.day} {NAMA_BULAN[monday.month]} {monday.year}"
            # key = (year, week_num)
            # label = f"Minggu {week_num} ({tgl_mulai})"
            from datetime import timedelta
            monday = dt - timedelta(days=dt.weekday())
            week_of_month = (monday.day - 1) // 7 + 1
            label = f"{NAMA_BULAN[monday.month]} W{week_of_month} ({monday.year})"
            key = (year, week_num)
            week_map[key][row['Label']] += 1
            week_map[key]['label'] = label
            week_map[key]['_year'] = year
            week_map[key]['_week'] = week_num

        # Urutkan berdasarkan tahun & nomor minggu
        sorted_keys = sorted(week_map.keys())
        weekly_trend = [week_map[k] for k in sorted_keys]

    except Exception as e:
        print("Weekly trend error:", e)

    # ── Word Cloud dari data preprocessing ────────────────────────────
    try:
        cur.execute("""
            SELECT dp.text_preprocessed, ds.Label
            FROM data_preprocessing dp
            JOIN data_sentimen ds ON dp.sentimen_id = ds.id
        """)
        prep_rows     = cur.fetchall()
        word_freq_pos = defaultdict(int)
        word_freq_neg = defaultdict(int)
        for row in prep_rows:
            for word in row['text_preprocessed'].split():
                if row['Label'] == 'Positif':
                    word_freq_pos[word] += 1
                else:
                    word_freq_neg[word] += 1

        def make_wordcloud(freq_dict, top_n=40):
            sorted_words = sorted(freq_dict.items(), key=lambda x: x[1], reverse=True)[:top_n]
            if not sorted_words:
                return []
            max_count = sorted_words[0][1]
            return [{'word': w, 'count': c,
                     'size': int(14 + (c / max_count) * 32)}
                    for w, c in sorted_words]

        wordcloud_pos = make_wordcloud(word_freq_pos)
        wordcloud_neg = make_wordcloud(word_freq_neg)
    except Exception as e:
        print("Wordcloud error:", e)

    cur.close()
    conn.close()

    return render_template('dashboard.html',
        totals=totals,
        latest_accuracy=latest_accuracy,
        sentiment_counts=sentiment_counts,
        train_counts=train_counts,
        test_counts=test_counts,
        weekly_trend=weekly_trend,
        wordcloud_pos=wordcloud_pos,
        wordcloud_neg=wordcloud_neg)


# ── Upload CSV config ──────────────────────────────────────────────────
UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
ALLOWED_EXTENSIONS = {'csv'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


# ── Data Sentimen ──────────────────────────────────────────────────────
@app.route('/data_sentimen')
@login_required
@admin_required
def data_sentimen():
    conn     = get_db_conn()
    cur      = conn.cursor(dictionary=True)
    page     = request.args.get('page', 1, type=int)
    per_page = request.args.get('limit', 25, type=int)
    offset   = (page - 1) * per_page

    cur.execute("SELECT COUNT(*) as total FROM data_sentimen")
    total_data  = cur.fetchone()['total']
    total_pages = max(1, (total_data + per_page - 1) // per_page)

    cur.execute("SELECT * FROM data_sentimen ORDER BY id DESC LIMIT %s OFFSET %s",
                (per_page, offset))
    data = cur.fetchall()
    cur.close()
    conn.close()
    return render_template('data_sentimen.html',
        data=data, page=page, total_pages=total_pages, per_page=per_page)


# ── Import CSV ─────────────────────────────────────────────────────────
@app.route('/import_sentimen', methods=['POST'])
@login_required
@admin_required
def import_sentimen():
    file = request.files.get('file')
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)

        try:
            df = pd.read_csv(filepath, encoding='utf-8', sep=';')
        except UnicodeDecodeError:
            df = pd.read_csv(filepath, encoding='latin1', sep=';')

        rename_map = {}
        if 'full_text'  in df.columns: rename_map['full_text']  = 'text'
        if 'label'      in df.columns: rename_map['label']      = 'Label'
        if 'created_at' in df.columns and 'createTimeISO' not in df.columns:
            rename_map['created_at'] = 'createTimeISO'
        df = df.rename(columns=rename_map)

        if 'Label' not in df.columns or 'text' not in df.columns:
            flash("❌ Kolom 'text' atau 'Label' tidak ditemukan di CSV!", "danger")
            return redirect(url_for('data_sentimen'))

        df['Label'] = df['Label'].astype(str).str.strip().str.capitalize()
        df = df[df['Label'].isin(['Positif', 'Negatif'])]

        data = [(row.get('createTimeISO', ''), row['text'], row['Label'])
                for _, row in df.iterrows()]

        conn = get_db_conn()
        cur  = conn.cursor()
        cur.executemany(
            "INSERT INTO data_sentimen (createTimeISO, text, Label) VALUES (%s,%s,%s)", data)
        conn.commit()
        cur.close()
        conn.close()
        flash(f"✅ {len(data)} data CSV berhasil diimport!", "success")
    else:
        flash("❌ Format file tidak valid! Harus .csv", "danger")
    return redirect(url_for('data_sentimen'))


# ── Preprocessing ──────────────────────────────────────────────────────
@app.route('/preprocessing')
@login_required
def preprocessing_page():
    page     = int(request.args.get('page', 1))
    per_page = int(request.args.get('limit', 25))
    conn     = get_db_conn()
    cursor   = conn.cursor(dictionary=True)
    cursor.execute("SELECT COUNT(*) as total FROM data_preprocessing")
    total_data  = cursor.fetchone()['total']
    total_pages = max(1, (total_data + per_page - 1) // per_page)
    offset      = (page - 1) * per_page
    cursor.execute("SELECT * FROM data_preprocessing ORDER BY sentimen_id ASC LIMIT %s OFFSET %s",
                   (per_page, offset))
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template('preprocessing.html',
        data_prep=rows, page=page, per_page=per_page, total_pages=total_pages)


@app.route('/preprocessing/run', methods=['POST'])
@login_required
def run_preprocessing():
    conn   = get_db_conn()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT id, text FROM data_sentimen")
    rows = cursor.fetchall()

    if not rows:
        flash("⚠️ Tidak ada data untuk diproses.", "warning")
        cursor.close()
        conn.close()
        return redirect(url_for('preprocessing_page'))

    df = pd.DataFrame(rows)
    df['preprocessed'] = df['text'].apply(preprocess_pipeline)

    cursor.execute("DELETE FROM data_preprocessing")
    values = [(r['id'], r['text'], ' '.join(r['preprocessed'])) for _, r in df.iterrows()]
    cursor.executemany(
        "INSERT INTO data_preprocessing (sentimen_id, text_original, text_preprocessed) VALUES (%s,%s,%s)",
        values)
    conn.commit()
    cursor.close()
    conn.close()
    flash(f"✅ Preprocessing selesai! {len(values)} data diproses.", "success")
    return redirect(url_for('preprocessing_page'))

@app.route('/preprocessing/download')
@login_required
def download_preprocessing():
    import io, csv
    from flask import Response
    from utils.preprocessing import (
        lowercase, remove_mention_url, normalize_slang_text,
        negation_handling_text, tokenize
    )

    conn   = get_db_conn()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT dp.sentimen_id,
               dp.text_original,
               dp.text_preprocessed,
               ds.Label
        FROM data_preprocessing dp
        JOIN data_sentimen ds ON dp.sentimen_id = ds.id
        ORDER BY dp.sentimen_id ASC
    """)
    rows = cursor.fetchall()
    cursor.close()
    conn.close()

    if not rows:
        flash("⚠️ Belum ada data preprocessing untuk didownload.", "warning")
        return redirect(url_for('preprocessing_page'))

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['sentimen_id', 'teks_asli', 'teks_clean', 'teks_token', 'teks_final', 'label'])

    for r in rows:
        raw        = str(r['text_original'])
        step2      = remove_mention_url(lowercase(raw))
        teks_clean = normalize_slang_text(step2)
        step4      = negation_handling_text(teks_clean)
        teks_token = ' '.join(tokenize(step4))

        # Format jadi ['kata1', 'kata2', ...]
        teks_final = str(r['text_preprocessed'].split())

        writer.writerow([
            r['sentimen_id'],
            raw,
            teks_clean,
            teks_token,
            teks_final,
            r['Label'],
        ])

    output.seek(0)
    return Response(
        '\ufeff' + output.getvalue(),
        mimetype='text/csv',
        headers={'Content-Disposition': 'attachment; filename=hasil_preprocessing.csv'}
    )


# ── Download TF, IDF, TF-IDF ───────────────────────────────────────────
@app.route('/download_tfidf')
@login_required
def download_tfidf():
    import io, csv
    from flask import Response
    from utils.tfidf import compute_tf, compute_idf, compute_tfidf

    # Cek apakah IDF sudah tersedia (model sudah pernah di-training)
    idf_path = os.path.join(MODEL_DIR, 'idf.pkl')
    if not os.path.exists(idf_path):
        flash("⚠️ IDF belum tersedia. Jalankan Training terlebih dahulu.", "warning")
        return redirect(request.referrer or url_for('dashboard'))

    idf = joblib.load(idf_path)

    conn   = get_db_conn()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT ds.createTimeISO,
               ds.text,
               ds.Label,
               dp.text_preprocessed AS preprocessed
        FROM data_preprocessing dp
        JOIN data_sentimen ds ON dp.sentimen_id = ds.id
        ORDER BY dp.sentimen_id ASC
    """)
    rows = cursor.fetchall()
    cursor.close()
    conn.close()

    if not rows:
        flash("⚠️ Belum ada data preprocessing. Jalankan Preprocessing terlebih dahulu.", "warning")
        return redirect(request.referrer or url_for('dashboard'))

    # Tokenisasi semua dokumen
    all_tokens = [r['preprocessed'].split() for r in rows]

    # Hitung TF untuk seluruh data
    tf_list    = compute_tf(all_tokens)

    # Hitung TF-IDF menggunakan IDF dari training
    tfidf_list = compute_tfidf(tf_list, idf)

    # Kumpulkan semua vocab (dari IDF training, urut alfabet)
    vocab_sorted = sorted(idf.keys())

    output = io.StringIO()
    writer = csv.writer(output)

    # ── Header ────────────────────────────────────────────────────────
    # Kolom info + kolom TF per kata + kolom IDF per kata + kolom TF-IDF per kata
    header_info  = ['createTimeISO', 'text', 'Label', 'preprocessed']
    header_tf    = [f'TF_{w}'    for w in vocab_sorted]
    header_idf   = [f'IDF_{w}'   for w in vocab_sorted]
    header_tfidf = [f'TFIDF_{w}' for w in vocab_sorted]
    writer.writerow(header_info + header_tf + header_idf + header_tfidf)

    # ── Baris data ────────────────────────────────────────────────────
    for row, tf_doc, tfidf_doc in zip(rows, tf_list, tfidf_list):
        info_cols = [
            row['createTimeISO'] or '',
            row['text'],
            row['Label'],
            row['preprocessed'],
        ]

        tf_cols    = [round(tf_doc.get(w, 0.0), 8)    for w in vocab_sorted]
        idf_cols   = [round(idf.get(w, 0.0), 8)        for w in vocab_sorted]
        tfidf_cols = [round(tfidf_doc.get(w, 0.0), 8) for w in vocab_sorted]

        writer.writerow(info_cols + tf_cols + idf_cols + tfidf_cols)

    output.seek(0)
    return Response(
        '\ufeff' + output.getvalue(),
        mimetype='text/csv',
        headers={'Content-Disposition': 'attachment; filename=hasil_tfidf.csv'}
    )


# ── Data Training Page ─────────────────────────────────────────────────
@app.route('/data_training')
@login_required
def data_training_page():
    page     = int(request.args.get('page', 1))
    per_page = int(request.args.get('limit', 25))
    conn     = get_db_conn()
    cursor   = conn.cursor(dictionary=True)
    cursor.execute("SELECT COUNT(*) as total FROM data_training")
    total_data  = cursor.fetchone()['total']
    total_pages = max(1, (total_data + per_page - 1) // per_page)
    offset      = (page - 1) * per_page
    cursor.execute("SELECT * FROM data_training ORDER BY id ASC LIMIT %s OFFSET %s",
                   (per_page, offset))
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template('data_training.html',
        data_train=rows, page=page, per_page=per_page, total_pages=total_pages)


# ── Data Testing Page ──────────────────────────────────────────────────
@app.route('/data_testing')
@login_required
def data_testing_page():
    page     = int(request.args.get('page', 1))
    per_page = int(request.args.get('limit', 25))
    conn     = get_db_conn()
    cursor   = conn.cursor(dictionary=True)
    cursor.execute("SELECT COUNT(*) as total FROM data_testing")
    total_data  = cursor.fetchone()['total']
    total_pages = max(1, (total_data + per_page - 1) // per_page)
    offset      = (page - 1) * per_page
    cursor.execute("SELECT * FROM data_testing ORDER BY id ASC LIMIT %s OFFSET %s",
                   (per_page, offset))
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template('data_testing.html',
        data_test=rows, page=page, per_page=per_page, total_pages=total_pages)


# ══════════════════════════════════════════════════════════════════════
# TRAINING
# ══════════════════════════════════════════════════════════════════════
@app.route('/training_proses')
@login_required
def training_proses():
    try:
        conn = get_db_conn()
        cur  = conn.cursor(dictionary=True)
        cur.execute("""
            SELECT dp.text_original     AS original,
                   dp.text_preprocessed AS preprocessed,
                   ds.Label
            FROM data_preprocessing dp
            JOIN data_sentimen ds ON dp.sentimen_id = ds.id
        """)
        rows = cur.fetchall()
        cur.close()
        conn.close()

        if not rows:
            return jsonify({'status': 'error',
                            'message': 'Data preprocessing kosong. Jalankan preprocessing terlebih dahulu.'})

        df = pd.DataFrame(rows)

        train_df, test_df = train_test_split(
            df, test_size=0.2, stratify=df['Label'], random_state=42)

        train_tokens = [text.split() for text in train_df['preprocessed'].tolist()]
        test_tokens  = [text.split() for text in test_df['preprocessed'].tolist()]

        tfidf_train, tfidf_test, idf, vocab = build_tfidf(train_tokens, test_tokens)

        joblib.dump(idf,   os.path.join(MODEL_DIR, 'idf.pkl'))
        joblib.dump(vocab, os.path.join(MODEL_DIR, 'vocab.pkl'))

        # ── SMOTE Oversampling ────────────────────────────────────────────
        # Ubah TF-IDF dict menjadi matrix numerik agar bisa di-SMOTE
        smote_applied    = False
        y_train_labels   = train_df['Label'].tolist()
        tfidf_train_final = tfidf_train

        if SMOTE_AVAILABLE:
            try:
                # Kumpulkan semua vocab dari training
                all_words = sorted(vocab)
                word2idx  = {w: i for i, w in enumerate(all_words)}
                n_features = len(all_words)

                # Buat matrix (n_samples x n_features)
                import numpy as np
                X_mat = np.zeros((len(tfidf_train), n_features), dtype=np.float32)
                for i, doc in enumerate(tfidf_train):
                    for w, v in doc.items():
                        if w in word2idx:
                            X_mat[i, word2idx[w]] = v

                # Encode label ke integer
                label_list   = sorted(set(y_train_labels))  # ['Negatif', 'Positif']
                label2int    = {l: i for i, l in enumerate(label_list)}
                int2label    = {i: l for l, i in label2int.items()}
                y_int        = np.array([label2int[l] for l in y_train_labels])

                # Hitung k_neighbors yang aman (min kelas - 1, max 5)
                from collections import Counter
                class_counts = Counter(y_train_labels)
                min_class_count = min(class_counts.values())
                k_neighbors = min(5, min_class_count - 1)

                if k_neighbors >= 1:
                    sm = SMOTE(random_state=42, k_neighbors=k_neighbors)
                    X_resampled, y_resampled = sm.fit_resample(X_mat, y_int)

                    # Konversi balik ke list of dict TF-IDF
                    tfidf_train_final = []
                    for row in X_resampled:
                        doc = {all_words[j]: float(row[j])
                               for j in range(n_features) if row[j] > 0}
                        tfidf_train_final.append(doc)

                    y_train_labels  = [int2label[i] for i in y_resampled]
                    smote_applied   = True

                    # Simpan info balancing untuk response
                    before_counts = dict(class_counts)
                    after_counts  = dict(Counter(y_train_labels))
                else:
                    before_counts = dict(Counter(y_train_labels))
                    after_counts  = before_counts

            except Exception as e_smote:
                print(f'[SMOTE] Gagal: {e_smote}, lanjut tanpa SMOTE.')
                before_counts = dict(Counter(y_train_labels))
                after_counts  = before_counts
        else:
            before_counts = dict(Counter(y_train_labels))
            after_counts  = before_counts

        nb_model = ManualNaiveBayes(alpha=1.0)
        nb_model.fit(tfidf_train_final, y_train_labels)

        joblib.dump(nb_model, os.path.join(MODEL_DIR, 'naive_bayes_model.pkl'))

        nb_summary = nb_model.get_summary(top_n=10)
        with open(os.path.join(MODEL_DIR, 'nb_summary.json'), 'w') as f:
            json.dump(nb_summary, f, ensure_ascii=False, indent=2)

        conn = get_db_conn()
        cur  = conn.cursor()
        cur.execute("DELETE FROM data_training")
        cur.execute("DELETE FROM data_testing")
        for _, row in train_df.iterrows():
            cur.execute(
                "INSERT INTO data_training (text, Label, preprocessed) VALUES (%s,%s,%s)",
                (row['original'], row['Label'], row['preprocessed']))
        for _, row in test_df.iterrows():
            cur.execute(
                "INSERT INTO data_testing (text, Label, preprocessed) VALUES (%s,%s,%s)",
                (row['original'], row['Label'], row['preprocessed']))
        conn.commit()
        cur.close()
        conn.close()

        smote_msg = (
            f' (SMOTE: {before_counts} → {after_counts})' 
            if smote_applied else ' (SMOTE tidak tersedia, install imbalanced-learn)'
        )
        return jsonify({
            'status'         : 'success',
            'message'        : 'Model Naive Bayes berhasil di-training!' + smote_msg,
            'total_train'    : len(tfidf_train_final),
            'total_train_ori': len(train_df),
            'total_test'     : len(test_df),
            'vocab_size'     : len(vocab),
            'smote_applied'  : smote_applied,
            'before_counts'  : before_counts,
            'after_counts'   : after_counts,
        })

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'status': 'error', 'message': str(e)})


# ══════════════════════════════════════════════════════════════════════
# TESTING
# ══════════════════════════════════════════════════════════════════════
@app.route('/testing_proses')
@login_required
def testing_proses():
    try:
        model_path = os.path.join(MODEL_DIR, 'naive_bayes_model.pkl')
        idf_path   = os.path.join(MODEL_DIR, 'idf.pkl')

        if not os.path.exists(model_path):
            return jsonify({'status': 'error',
                            'message': 'Model belum ditraining. Jalankan training terlebih dahulu.'})
        if not os.path.exists(idf_path):
            return jsonify({'status': 'error',
                            'message': 'IDF belum tersedia. Jalankan training terlebih dahulu.'})

        nb_model = joblib.load(model_path)
        idf      = joblib.load(idf_path)

        conn = get_db_conn()
        cur  = conn.cursor(dictionary=True)
        cur.execute("SELECT id, text, preprocessed, Label FROM data_testing")
        rows = cur.fetchall()
        cur.close()
        conn.close()

        if not rows:
            return jsonify({'status': 'error',
                            'message': 'Data testing kosong. Jalankan training terlebih dahulu.'})

        df          = pd.DataFrame(rows)
        test_tokens = [text.split() for text in df['preprocessed'].tolist()]
        y_test      = df['Label'].tolist()

        tf_test    = compute_tf(test_tokens)
        tfidf_test = compute_tfidf(tf_test, idf)

        y_pred, posteriors = nb_model.predict_with_posterior(tfidf_test)

        acc  = accuracy_score(y_test, y_pred)
        prec = precision_score(y_test, y_pred, average='weighted', zero_division=0)
        rec  = recall_score(y_test, y_pred, average='weighted', zero_division=0)
        f1   = f1_score(y_test, y_pred, average='weighted', zero_division=0)
        cm     = confusion_matrix(y_test, y_pred)
        labels = sorted(list(set(y_test)))

        misclassified = []
        for i, (true, pred) in enumerate(zip(y_test, y_pred)):
            if true != pred:
                misclassified.append({
                    'text'     : df.iloc[i]['preprocessed'],
                    'actual'   : true,
                    'predicted': pred,
                    'posterior': posteriors[i]
                })

        posterior_sample = []
        for i in range(min(5, len(df))):
            posterior_sample.append({
                'text'     : df.iloc[i]['preprocessed'][:100] + '...',
                'posterior': posteriors[i],
                'predicted': y_pred[i],
                'actual'   : y_test[i]
            })
        with open(os.path.join(MODEL_DIR, 'posterior_sample.json'), 'w') as f:
            json.dump(posterior_sample, f, ensure_ascii=False, indent=2)

        conn = get_db_conn()
        cur  = conn.cursor()
        cur.execute("""
            INSERT INTO hasil_analisis
            (model, accuracy, precisionn, recall, f1_score, confusion_matrix, misclassified, created_at)
            VALUES (%s,%s,%s,%s,%s,%s,%s,NOW())
        """, (
            'Naive Bayes', acc, prec, rec, f1,
            json.dumps({"labels": labels, "matrix": cm.tolist()}),
            json.dumps(misclassified[:50])
        ))
        conn.commit()
        cur.close()
        conn.close()

        return jsonify({
            "status"   : "success",
            "accuracy" : round(acc  * 100, 2),
            "precision": round(prec * 100, 2),
            "recall"   : round(rec  * 100, 2),
            "f1_score" : round(f1   * 100, 2)
        })

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"status": "error", "message": str(e)})


# ── Hasil Analisis ─────────────────────────────────────────────────────
@app.route('/hasil_analisis', methods=['GET'])
@login_required
def result_page():
    conn   = get_db_conn()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM hasil_analisis ORDER BY created_at DESC")
    hasil_data = cursor.fetchall()
    cursor.execute("SELECT * FROM hasil_analisis ORDER BY created_at DESC LIMIT 1")
    hasil = cursor.fetchone()
    
    # Cek apakah ada data training (untuk menentukan apakah file model perlu ditampilkan)
    cursor.execute("SELECT COUNT(*) as cnt FROM data_training")
    train_count = cursor.fetchone()['cnt']
    
    cursor.close()
    conn.close()

    if hasil and hasil.get('confusion_matrix'):
        try:
            cm_dict = json.loads(hasil['confusion_matrix'])
            if 'labels' in cm_dict and 'matrix' in cm_dict:
                hasil['confusion_matrix'] = cm_dict
            else:
                labels = list(cm_dict.keys())
                matrix = [[cm_dict[a].get(p, 0) for p in labels] for a in labels]
                hasil['confusion_matrix'] = {"labels": labels, "matrix": matrix}
        except Exception:
            hasil['confusion_matrix'] = None

    if hasil and hasil.get('misclassified'):
        try:
            hasil['misclassified'] = json.loads(hasil['misclassified'])
        except:
            hasil['misclassified'] = None

    if hasil:
        for field in ['accuracy', 'precisionn', 'recall', 'f1_score']:
            if hasil.get(field) is not None:
                hasil[field] = round(hasil[field] * 100, 2)

    # ⭐ PERUBAHAN: Hanya load file model jika ada data training (train_count > 0)
    nb_summary       = None
    posterior_sample = None
    if train_count > 0:
        if os.path.exists(os.path.join(MODEL_DIR, 'nb_summary.json')):
            with open(os.path.join(MODEL_DIR, 'nb_summary.json')) as f:
                nb_summary = json.load(f)
        if os.path.exists(os.path.join(MODEL_DIR, 'posterior_sample.json')):
            with open(os.path.join(MODEL_DIR, 'posterior_sample.json')) as f:
                posterior_sample = json.load(f)

    return render_template('result.html',
        hasil_data=hasil_data,
        hasil=hasil,
        nb_summary=nb_summary,
        posterior_sample=posterior_sample,
        active_page='result')


# ── Users ──────────────────────────────────────────────────────────────
@app.route('/users', methods=['GET', 'POST'])
@login_required
@admin_required
def users_page():
    conn    = get_db_conn()
    cur     = conn.cursor(dictionary=True)
    message = None
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email    = request.form.get('email', '').strip()
        password = request.form.get('password', '').strip()
        role     = request.form.get('role', 'user')
        if not username or not email or not password:
            message = '❌ Semua field harus diisi.'
        else:
            try:
                cur.execute(
                    'INSERT INTO users (username,email,password,role) VALUES (%s,%s,%s,%s)',
                    (username, email, generate_password_hash(password), role))
                conn.commit()
                flash('✅ User berhasil ditambahkan.', 'success')
            except Exception as e:
                conn.rollback()
                flash(f'❌ Gagal: {str(e)}', 'danger')
    cur.execute('SELECT id,username,email,role,created_at FROM users ORDER BY id DESC')
    users = cur.fetchall()
    cur.close()
    conn.close()
    return render_template('users.html', users=users, message=message)


@app.route('/users/delete/<int:user_id>', methods=['POST'])
@login_required
@admin_required
def delete_user(user_id):
    if user_id == session.get('user_id'):
        flash("❌ Tidak bisa menghapus akun sendiri.", "danger")
        return redirect(url_for('users_page'))
    conn = get_db_conn()
    cur  = conn.cursor()
    try:
        cur.execute("DELETE FROM users WHERE id=%s", (user_id,))
        conn.commit()
        flash("🗑️ User berhasil dihapus.", "success")
    except Exception as e:
        conn.rollback()
        flash(f"❌ Gagal: {str(e)}", "danger")
    cur.close()
    conn.close()
    return redirect(url_for('users_page'))


@app.route('/edit_user/<int:user_id>', methods=['POST'])
@login_required
@admin_required
def edit_user(user_id):
    username = request.form['username']
    email    = request.form['email']
    password = request.form['password']
    role     = request.form['role']
    conn = get_db_conn()
    cur  = conn.cursor()
    if password.strip() == "":
        cur.execute("UPDATE users SET username=%s,email=%s,role=%s WHERE id=%s",
                    (username, email, role, user_id))
    else:
        cur.execute("UPDATE users SET username=%s,email=%s,password=%s,role=%s WHERE id=%s",
                    (username, email, generate_password_hash(password), role, user_id))
    conn.commit()
    cur.close()
    conn.close()
    flash('✅ User berhasil diperbarui!', 'success')
    return redirect(url_for('users_page'))


# ── Login / Register / Logout ──────────────────────────────────────────
@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        email    = request.form['email']
        password = request.form['password']
        db       = get_db_conn()
        cursor   = db.cursor(dictionary=True, buffered=True)
        cursor.execute("SELECT * FROM users WHERE email=%s", (email,))
        user = cursor.fetchone()
        cursor.close()
        db.close()
        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['id']
            session['nama']    = user['username']
            session['role']    = user['role']
            flash(f"Selamat datang, {user['username']}!", "success")
            return redirect(url_for('dashboard'))
        else:
            flash('Email atau password salah!', 'danger')
    return render_template('login.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        username        = request.form.get('username', '').strip()
        email           = request.form.get('email', '').strip()
        password        = request.form.get('password', '').strip()
        confirm_password = request.form.get('confirm_password', '').strip()
        role            = request.form.get('role', 'user').strip()

        # Validasi konfirmasi password
        if password != confirm_password:
            flash('Password dan konfirmasi password tidak cocok.', 'danger')
            return render_template('register.html')

        if not username or not email or not password:
            flash('Semua field harus diisi.', 'danger')
            return render_template('register.html')

        db = get_db_conn()
        cursor = db.cursor(dictionary=True, buffered=True)
        cursor.execute("SELECT * FROM users WHERE email=%s OR username=%s", (email, username))
        if cursor.fetchone():
            cursor.close()
            db.close()
            flash('Email atau nama pengguna sudah terdaftar.', 'danger')
            return render_template('register.html')

        hashed = generate_password_hash(password)
        cursor.execute(
            "INSERT INTO users (username, email, password, role) VALUES (%s, %s, %s, %s)",
            (username, email, hashed, role)
        )
        db.commit()
        cursor.close()
        db.close()
        flash('Akun berhasil dibuat. Silakan login.', 'success')
        return redirect(url_for('login'))

    return render_template('register.html')

@app.route('/logout')
@login_required
def logout():
    session.clear()
    flash("Anda telah logout.", "info")
    return redirect(url_for('login'))


@app.route('/hapus_data/<string:tabel>', methods=['POST'])
@login_required
@admin_required
def hapus_data(tabel):
    conn    = get_db_conn()
    cursor  = conn.cursor()
    allowed = ['data_sentimen', 'data_preprocessing', 'data_training', 'data_testing', 'hasil_analisis']
    if tabel not in allowed:
        cursor.close()
        conn.close()
        flash("❌ Tabel tidak valid!", "danger")
        return redirect(request.referrer or url_for('dashboard'))
    try:
        cursor.execute(f"DELETE FROM {tabel}")
        conn.commit()
        flash(f"✅ Data {tabel} berhasil dihapus!", "success")
    except Exception as e:
        conn.rollback()
        flash(f"❌ Gagal menghapus: {e}", "danger")
    cursor.close()
    conn.close()
    return redirect(request.referrer or url_for('dashboard'))


# ── Predict API ────────────────────────────────────────────────────────
@app.route('/predict', methods=['POST'])
@login_required
def predict_api():
    payload = request.json
    text    = payload.get('text', '')
    if not text:
        return jsonify({'error': 'Teks tidak boleh kosong'}), 400

    model_path = os.path.join(MODEL_DIR, 'naive_bayes_model.pkl')
    idf_path   = os.path.join(MODEL_DIR, 'idf.pkl')
    if not os.path.exists(model_path) or not os.path.exists(idf_path):
        return jsonify({'error': 'Model belum tersedia'}), 500

    nb_model  = joblib.load(model_path)
    idf       = joblib.load(idf_path)

    tokens    = preprocess_pipeline(text)
    tfidf_doc = build_tfidf_single(tokens, idf)

    preds, posteriors = nb_model.predict_with_posterior([tfidf_doc])
    return jsonify({'prediction': preds[0], 'posterior': posteriors[0]})


if __name__ == '__main__':
    app.run(debug=True)