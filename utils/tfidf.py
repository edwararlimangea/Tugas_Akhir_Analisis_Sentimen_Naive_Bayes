# utils/tfidf.py
# Implementasi manual TF-IDF sesuai rumus:
#   TF = 1 + log(freq) jika freq > 0
#   IDF = log(D / df)
#   TF-IDF = TF * IDF

import math


def compute_tf(docs):
    """
    Hitung Term Frequency dengan rumus: TF = 1 + log(F)
    Args:
        docs: list of list of str (token per dokumen)
    Returns:
        list of dict {word: tf_value}
    """
    tf_list = []
    for tokens in docs:
        tf = {}
        # Hitung frekuensi absolut kata dalam dokumen
        freq = {}
        for w in tokens:
            freq[w] = freq.get(w, 0) + 1
        # Terapkan rumus TF = 1 + log(freq)
        for w, f in freq.items():
            if f > 0:
                # tf[w] = 1 + math.log(f)
                tf[w] = 1 + math.log10(f)
        tf_list.append(tf)
    return tf_list


def compute_idf(docs):
    """
    Hitung Inverse Document Frequency dengan rumus: IDF = log(D / df)
    Args:
        docs: list of list of str (token per dokumen training)
    Returns:
        dict {word: idf_value}
    """
    D = len(docs)
    # Hitung document frequency (jumlah dokumen yang mengandung kata)
    df = {}
    for tokens in docs:
        unique_words = set(tokens)
        for w in unique_words:
            df[w] = df.get(w, 0) + 1
    
    idf = {}
    for w, freq in df.items():
        # D / freq > 0 karena freq minimal 1
        idf[w] = math.log10(D / freq)
        # idf[w] = math.log(D / freq)
    return idf


def compute_tfidf(tf_list, idf):
    """
    Hitung TF-IDF = TF * IDF
    Args:
        tf_list: output dari compute_tf
        idf: output dari compute_idf
    Returns:
        list of dict {word: tfidf_value}
    """
    tfidf_list = []
    for tf in tf_list:
        tfidf = {w: tf_val * idf.get(w, 0.0) for w, tf_val in tf.items()}
        tfidf_list.append(tfidf)
    return tfidf_list


def build_tfidf(train_tokens, test_tokens):
    """
    Pipeline lengkap TF-IDF untuk training dan testing.
    IDF dihitung HANYA dari data training.
    Args:
        train_tokens: list of list of str
        test_tokens: list of list of str
    Returns:
        tfidf_train, tfidf_test, idf, vocab
    """
    # Hitung TF untuk training dan testing
    tf_train = compute_tf(train_tokens)
    tf_test = compute_tf(test_tokens)

    # Hitung IDF hanya dari training
    idf = compute_idf(train_tokens)
    vocab = set(idf.keys())

    # Hitung TF-IDF
    tfidf_train = compute_tfidf(tf_train, idf)
    tfidf_test = compute_tfidf(tf_test, idf)

    return tfidf_train, tfidf_test, idf, vocab


def build_tfidf_single(tokens, idf):
    """
    Hitung TF-IDF untuk satu dokumen baru menggunakan IDF yang sudah ada.
    Args:
        tokens: list of str
        idf: dict IDF dari training
    Returns:
        dict {word: tfidf_value}
    """
    tf = compute_tf([tokens])[0]
    tfidf = compute_tfidf([tf], idf)[0]
    return tfidf