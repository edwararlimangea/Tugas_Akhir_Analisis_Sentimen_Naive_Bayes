# utils/split_data.py
# Utilitas untuk membagi dataset secara manual tanpa sklearn.
# Catatan: app.py menggunakan sklearn train_test_split yang sudah stratified.
# File ini disediakan sebagai alternatif / untuk keperluan dokumentasi.

import pandas as pd
from random import shuffle, seed as set_seed


def split_dataset(df: pd.DataFrame, split_ratio: float = 0.8, random_seed: int = 42) -> tuple:
    """
    Bagi DataFrame menjadi data training dan testing secara manual.

    Args:
        df          : DataFrame yang akan dibagi
        split_ratio : Proporsi data training (default 0.8 = 80%)
        random_seed : Seed untuk reproducibility (default 42)

    Returns:
        train_df, test_df
    """
    set_seed(random_seed)
    data = df.to_dict('records')
    shuffle(data)

    split_idx  = int(len(data) * split_ratio)
    train_data = data[:split_idx]
    test_data  = data[split_idx:]

    train_df = pd.DataFrame(train_data)
    test_df  = pd.DataFrame(test_data)

    print(f"✅ Split selesai — Training: {len(train_df)}, Testing: {len(test_df)}")
    return train_df, test_df


def split_dataset_stratified(df: pd.DataFrame, label_col: str = 'Label',
                              split_ratio: float = 0.8, random_seed: int = 42) -> tuple:
    """
    Bagi DataFrame dengan menjaga proporsi kelas (stratified split).

    Args:
        df          : DataFrame yang akan dibagi
        label_col   : Nama kolom label
        split_ratio : Proporsi data training
        random_seed : Seed untuk reproducibility

    Returns:
        train_df, test_df
    """
    set_seed(random_seed)
    train_list = []
    test_list  = []

    for label, group in df.groupby(label_col):
        data = group.to_dict('records')
        shuffle(data)
        split_idx = int(len(data) * split_ratio)
        train_list.extend(data[:split_idx])
        test_list.extend(data[split_idx:])

    # Shuffle ulang agar tidak berurutan per kelas
    shuffle(train_list)
    shuffle(test_list)

    train_df = pd.DataFrame(train_list)
    test_df  = pd.DataFrame(test_list)

    print(f"✅ Stratified split — Training: {len(train_df)}, Testing: {len(test_df)}")
    return train_df, test_df