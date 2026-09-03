import pandas as pd
import numpy as np

def extract_behavioral_features(transactions_df: pd.DataFrame) -> pd.DataFrame:
    """Extract behavioral features per transaction.
    
    Features (computed per customer up to the current transaction's timestamp):
    - avg_transaction_amount: running average of customer's past transaction amounts
    - amount_deviation: (current_amount - avg) / std, capped at [-5, 5]
    - refund_rate: fraction of customer's past transactions that are refunds
    - merchant_count: number of distinct merchants the customer has transacted with so far
    - device_count: number of distinct devices the customer has used so far
    - instrument_count: number of distinct payment instruments the customer has used so far
    """
    df = transactions_df.copy()
    if 'amount' in df.columns:
        df['amount'] = df['amount'].astype(float)
    df['occurred_at'] = pd.to_datetime(df['occurred_at'])
    df = df.sort_values(['customer_id', 'occurred_at']).reset_index(drop=False)
    
    grouped = df.groupby('customer_id')
    
    df['avg_transaction_amount'] = grouped['amount'].apply(lambda x: x.shift().expanding().mean()).reset_index(level=0, drop=True).fillna(0)
    std_amount = grouped['amount'].apply(lambda x: x.shift().expanding().std()).reset_index(level=0, drop=True).fillna(1).replace(0, 1)
    
    df['amount_deviation'] = (df['amount'] - df['avg_transaction_amount']) / std_amount
    df['amount_deviation'] = df['amount_deviation'].clip(-5, 5)
    
    type_col = df['type'] if 'type' in df.columns else df['transaction_type'] if 'transaction_type' in df.columns else None
    if type_col is not None:
        df['is_refund'] = (type_col == 'refund').astype(int)
        df['refund_rate'] = grouped['is_refund'].apply(lambda x: x.shift().expanding().mean()).reset_index(level=0, drop=True).fillna(0)
    else:
        df['refund_rate'] = 0.0
        
    def count_distinct_past(col):
        if col not in df.columns:
            return 0
        return grouped[col].apply(lambda x: (~x.duplicated()).cumsum().shift().fillna(0)).reset_index(level=0, drop=True)
        
    df['merchant_count'] = count_distinct_past('merchant_id')
    df['device_count'] = count_distinct_past('device_id')
    df['instrument_count'] = count_distinct_past('instrument_id')
    
    return df.set_index('index').sort_index()
