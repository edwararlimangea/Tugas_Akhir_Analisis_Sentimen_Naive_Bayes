# config.py
import os
import mysql.connector


def get_db_connection():
    """
    Membuat koneksi ke database MySQL.
    Mendukung environment variable untuk konfigurasi fleksibel
    (development vs production).
    """
    return mysql.connector.connect(
        host     = os.environ.get('DB_HOST', 'localhost'),
        user     = os.environ.get('DB_USER', 'root'),
        password = os.environ.get('DB_PASS', ''),
        database = os.environ.get('DB_NAME', 'db_sentimen')
    )