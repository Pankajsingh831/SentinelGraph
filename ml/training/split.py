import pandas as pd

def chronological_split(features_df: pd.DataFrame, 
                        train_ratio: float = 0.70,
                        val_ratio: float = 0.15,
                        test_ratio: float = 0.15,
                        time_column: str = 'occurred_at') -> tuple:
    """Split dataset chronologically (oldest -> newest).
    
    Returns (train_df, val_df, test_df).
    Prints split statistics: date ranges, sizes, abuse ratios per split.
    """
    df = features_df.sort_values(by=time_column).copy()
    
    n = len(df)
    train_end = int(n * train_ratio)
    val_end = int(n * (train_ratio + val_ratio))
    
    train_df = df.iloc[:train_end]
    val_df = df.iloc[train_end:val_end]
    test_df = df.iloc[val_end:]
    
    print(f"Train size: {len(train_df)}, Val size: {len(val_df)}, Test size: {len(test_df)}")
    if 'is_abuse' in df.columns:
        print(f"Train abuse ratio: {train_df['is_abuse'].mean():.4f}")
        print(f"Val abuse ratio: {val_df['is_abuse'].mean():.4f}")
        print(f"Test abuse ratio: {test_df['is_abuse'].mean():.4f}")
        
    return train_df, val_df, test_df
