import pandas as pd
import numpy as np

def extract_temporal_features(transactions_df: pd.DataFrame) -> pd.DataFrame:
    """Extract time-based features per transaction.
    
    Features (computed per customer, looking ONLY at past transactions - no future leakage):
    - transaction_count_5m: transactions by same customer in preceding 5 minutes
    - transaction_count_1h: transactions by same customer in preceding 1 hour
    - transaction_count_24h: transactions by same customer in preceding 24 hours
    - time_since_previous_transaction: seconds since this customer's previous transaction
    - account_age_hours: hours between customer's account_created_at and transaction occurred_at
    - hour_of_day: hour (0-23) of the transaction
    - day_of_week: day of week (0-6)
    - is_night: binary, 1 if hour is 0-6
    - is_weekend: binary, 1 if Saturday or Sunday
    """
    df = transactions_df.copy()
    df['occurred_at'] = pd.to_datetime(df['occurred_at'])
    df = df.sort_values(['customer_id', 'occurred_at']).reset_index(drop=False)
    
    df['hour_of_day'] = df['occurred_at'].dt.hour
    df['day_of_week'] = df['occurred_at'].dt.dayofweek
    df['is_night'] = df['hour_of_day'].isin(range(0, 7)).astype(int)
    df['is_weekend'] = df['day_of_week'].isin([5, 6]).astype(int)
    
    if 'account_created_at' in df.columns:
        df['account_created_at'] = pd.to_datetime(df['account_created_at'])
        df['account_age_hours'] = (df['occurred_at'] - df['account_created_at']).dt.total_seconds() / 3600.0
    else:
        df['account_age_hours'] = 0.0
        
    df['time_since_previous_transaction'] = df.groupby('customer_id')['occurred_at'].diff().dt.total_seconds()
    df['time_since_previous_transaction'] = df['time_since_previous_transaction'].fillna(-1)
    
    # Calculate rolling counts
    # set index to occurred_at for rolling
    temp = df.set_index('occurred_at')
    
    df['transaction_count_5m'] = temp.groupby('customer_id')['transaction_id'].rolling('5min').count().values - 1
    df['transaction_count_1h'] = temp.groupby('customer_id')['transaction_id'].rolling('1h').count().values - 1
    df['transaction_count_24h'] = temp.groupby('customer_id')['transaction_id'].rolling('24h').count().values - 1
    
    # Fill any potential NaNs from rolling with 0
    df['transaction_count_5m'] = df['transaction_count_5m'].fillna(0)
    df['transaction_count_1h'] = df['transaction_count_1h'].fillna(0)
    df['transaction_count_24h'] = df['transaction_count_24h'].fillna(0)
    
    return df.set_index('index').sort_index()
