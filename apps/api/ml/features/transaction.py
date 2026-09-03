import pandas as pd
import numpy as np

def extract_transaction_features(transactions_df: pd.DataFrame) -> pd.DataFrame:
    """Extract transaction-level features.
    
    Features:
    - amount: raw transaction amount
    - amount_log: log-transformed amount (log1p)
    - is_refund: binary flag for refund transactions
    - is_transfer: binary flag for transfer transactions
    - merchant_category_encoded: label-encoded merchant category
    - currency_encoded: label-encoded currency
    """
    df = transactions_df.copy()
    
    if 'amount' in df.columns:
        df['amount'] = df['amount'].astype(float)
    df['amount_log'] = np.log1p(df.get('amount', pd.Series([0]*len(df))))
    
    type_col = df['type'] if 'type' in df.columns else df['transaction_type'] if 'transaction_type' in df.columns else None
    if type_col is not None:
        df['is_refund'] = (type_col == 'refund').astype(int)
        df['is_transfer'] = (type_col == 'transfer').astype(int)
    else:
        df['is_refund'] = 0
        df['is_transfer'] = 0
        
    if 'merchant_category' in df.columns:
        df['merchant_category_encoded'] = df['merchant_category'].astype('category').cat.codes
    else:
        df['merchant_category_encoded'] = 0
        
    if 'currency' in df.columns:
        df['currency_encoded'] = df['currency'].astype('category').cat.codes
    else:
        df['currency_encoded'] = 0
        
    return df
