# utils/tfidf_helper.py
# Helper TF-IDF menggunakan sklearn TfidfVectorizer.
# Digunakan untuk representasi teks pada proses training Naive Bayes.
# Model utama: ManualNaiveBayes dari utils/naive_bayes.py

import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
import joblib
import os

MODEL_DIR = 'model'
os.makedirs(MODEL_DIR, exist_ok=True)


def fetch_all_data_from_db(conn, table_name: str) -> pd.DataFrame:
    """Ambil seluruh data dari tabel DB ke DataFrame."""
    query = f"SELECT * FROM {table_name}"
    return pd.read_sql(query, conn)


def process_tfidf(train_df: pd.DataFrame, test_df: pd.DataFrame):
    """
    Hitung TF-IDF menggunakan sklearn TfidfVectorizer.
    Vectorizer di-fit hanya dari data training (tidak bocor ke test).

    Returns:
        X_train, X_test, y_train, y_test, vectorizer
    """
    if 'preprocessed' not in train_df.columns or 'preprocessed' not in test_df.columns:
        raise ValueError("DataFrame harus memiliki kolom 'preprocessed'")

    # Pastikan input adalah string
    train_texts = [
        ' '.join(tokens) if isinstance(tokens, list) else str(tokens)
        for tokens in train_df['preprocessed']
    ]
    test_texts = [
        ' '.join(tokens) if isinstance(tokens, list) else str(tokens)
        for tokens in test_df['preprocessed']
    ]

    vectorizer = TfidfVectorizer(max_features=5000, ngram_range=(1, 2))
    X_train = vectorizer.fit_transform(train_texts)
    X_test  = vectorizer.transform(test_texts)

    y_train = train_df['Label']
    y_test  = test_df['Label']

    return X_train, X_test, y_train, y_test, vectorizer


def save_vectorizer(vectorizer, model_dir: str = MODEL_DIR):
    """Simpan TF-IDF vectorizer ke disk."""
    joblib.dump(vectorizer, os.path.join(model_dir, 'tfidf_vectorizer.pkl'))


def predict_texts(list_of_texts: list, model_dir: str = MODEL_DIR) -> list:
    """
    Prediksi teks baru menggunakan model Naive Bayes yang sudah disimpan.

    Args:
        list_of_texts: list of str / list / dict dengan key 'text'
    Returns:
        list of str — label prediksi
    """
    model_path = os.path.join(model_dir, 'naive_bayes_model.pkl')
    vec_path   = os.path.join(model_dir, 'tfidf_vectorizer.pkl')

    if not os.path.exists(model_path) or not os.path.exists(vec_path):
        raise FileNotFoundError("Model atau vectorizer belum tersedia. Jalankan training terlebih dahulu.")

    model      = joblib.load(model_path)
    vectorizer = joblib.load(vec_path)

    processed_texts = []
    for item in list_of_texts:
        if isinstance(item, str):
            processed_texts.append(item)
        elif isinstance(item, dict) and 'text' in item:
            processed_texts.append(item['text'])
        elif isinstance(item, list):
            processed_texts.append(' '.join(item))
        else:
            processed_texts.append(str(item))

    X     = vectorizer.transform(processed_texts)
    preds = model.predict(X)
    return preds.tolist()