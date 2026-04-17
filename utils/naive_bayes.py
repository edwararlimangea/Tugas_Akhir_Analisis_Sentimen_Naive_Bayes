# utils/naive_bayes.py
# Implementasi Manual Naive Bayes sesuai flowchart:
#   Input  : vektor TF-IDF per dokumen (dict {word: tfidf_value})
#   Step 1 : Hitung Prior Probability   P(C)
#   Step 2 : Hitung Likelihood          P(w|C)  dengan Laplace smoothing
#   Step 3 : Hitung Posterior Probability P(C|d) untuk prediksi

import math
from collections import defaultdict


class ManualNaiveBayes:
    """
    Multinomial Naive Bayes dengan bobot TF-IDF.

    Alur sesuai flowchart:
        Representasi Text (TF → IDF → TF-IDF)
        → Prior Probability
        → Likelihood
        → Posterior Probability
        → Training Model
    """

    def __init__(self, alpha=1.0):
        self.alpha        = alpha
        self.classes      = []
        self.class_counts = {}
        self.word_scores  = {}   # akumulasi bobot TF-IDF per kata per kelas
        self.vocab        = set()
        self.total_docs   = 0
        self.prior        = {}
        self.likelihood   = {}

    # ══════════════════════════════════════════════════════════════════
    # TRAINING — menerima vektor TF-IDF dari tfidf.py
    # ══════════════════════════════════════════════════════════════════
    def fit(self, tfidf_train: list, y_labels: list):
        """
        Training Naive Bayes menggunakan bobot TF-IDF.

        Args:
            tfidf_train : list of dict {word: tfidf_value} — output dari tfidf.py
            y_labels    : list of str — label kelas ('Positif' / 'Negatif')
        """
        self.total_docs   = len(tfidf_train)
        self.classes      = sorted(list(set(y_labels)))
        self.class_counts = defaultdict(int)
        self.word_scores  = {c: defaultdict(float) for c in self.classes}

        # Akumulasi bobot TF-IDF per kata per kelas
        for tfidf_doc, label in zip(tfidf_train, y_labels):
            self.class_counts[label] += 1
            for word, tfidf_val in tfidf_doc.items():
                self.word_scores[label][word] += tfidf_val
                self.vocab.add(word)

        vocab_size = len(self.vocab)

        # ──────────────────────────────────────────────────────────────
        # STEP 1 — PRIOR PROBABILITY
        #          P(C) = jumlah_dokumen_kelas / total_dokumen
        # ──────────────────────────────────────────────────────────────
        self.prior = {
            c: self.class_counts[c] / self.total_docs
            for c in self.classes
        }

        # ──────────────────────────────────────────────────────────────
        # STEP 2 — LIKELIHOOD dengan Laplace smoothing
        #          P(w|C) = (score(w,C) + alpha) / (total_score_C + alpha * |V|)
        #          score  = akumulasi bobot TF-IDF kata w di kelas C
        # ──────────────────────────────────────────────────────────────
        self.likelihood = {}
        for c in self.classes:
            total_score = sum(self.word_scores[c].values())
            self.likelihood[c] = {}
            for word in self.vocab:
                score_wc = self.word_scores[c].get(word, 0.0)
                self.likelihood[c][word] = (
                    (score_wc + self.alpha) /
                    (total_score + self.alpha * vocab_size)
                )

        return self

    # ══════════════════════════════════════════════════════════════════
    # PREDIKSI — Hitung Posterior Probability
    # ══════════════════════════════════════════════════════════════════
    def predict_with_posterior(self, tfidf_docs: list):
        """
        STEP 3 — POSTERIOR PROBABILITY
                 P(C|d) ∝ P(C) * ∏ P(w|C)^tfidf(w,d)
                 Gunakan log-sum agar tidak underflow.

        Args:
            tfidf_docs : list of dict {word: tfidf_value}
        Returns:
            predictions : list of str
            posteriors  : list of dict {kelas: probabilitas}
        """
        predictions = []
        posteriors  = []
        vocab_size  = len(self.vocab)

        for tfidf_doc in tfidf_docs:
            log_posteriors = {}

            for c in self.classes:
                total_score = sum(self.word_scores[c].values())
                log_prob    = math.log(self.prior[c])

                for word, tfidf_val in tfidf_doc.items():
                    if word in self.likelihood[c]:
                        log_prob += tfidf_val * math.log(self.likelihood[c][word])
                    else:
                        smooth    = self.alpha / (total_score + self.alpha * vocab_size)
                        log_prob += tfidf_val * math.log(smooth)

                log_posteriors[c] = log_prob

            # Normalisasi ke probabilitas 0–1
            max_log  = max(log_posteriors.values())
            exp_vals = {c: math.exp(v - max_log) for c, v in log_posteriors.items()}
            total    = sum(exp_vals.values())
            norm_posteriors = {c: round(v / total, 6) for c, v in exp_vals.items()}

            best_class = max(norm_posteriors, key=norm_posteriors.get)
            predictions.append(best_class)
            posteriors.append(norm_posteriors)

        return predictions, posteriors

    def predict(self, tfidf_docs: list):
        preds, _ = self.predict_with_posterior(tfidf_docs)
        return preds

    # ══════════════════════════════════════════════════════════════════
    # RINGKASAN — untuk ditampilkan di halaman hasil
    # ══════════════════════════════════════════════════════════════════
    def get_summary(self, top_n=10):
        summary = {
            'total_docs'    : self.total_docs,
            'vocab_size'    : len(self.vocab),
            'classes'       : self.classes,
            'prior'         : {c: round(v, 6) for c, v in self.prior.items()},
            'class_counts'  : dict(self.class_counts),
            'top_likelihood': {}
        }
        for c in self.classes:
            sorted_words = sorted(
                self.likelihood[c].items(),
                key=lambda x: x[1], reverse=True
            )[:top_n]
            summary['top_likelihood'][c] = [
                {'word': w, 'prob': round(p, 8)} for w, p in sorted_words
            ]
        return summary