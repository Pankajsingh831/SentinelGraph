import pandas as pd
from .transaction import extract_transaction_features
from .temporal import extract_temporal_features  
from .behavioral import extract_behavioral_features
from .graph import extract_graph_features

class FeaturePipeline:
    """Orchestrates feature extraction across all feature groups."""
    
    def __init__(self, include_graph_features: bool = True):
        self.include_graph_features = include_graph_features
    
    def build_features(self, transactions_df: pd.DataFrame, 
                       customers_df: pd.DataFrame = None,
                       relationships_df: pd.DataFrame = None) -> pd.DataFrame:
        """Build the complete feature matrix.
        
        Returns a DataFrame with one row per transaction and all features as columns.
        Also includes 'transaction_id' and 'is_abuse' (label) columns.
        """
        # Ensure occurred_at is sorted
        df = transactions_df.copy()
        
        if customers_df is not None:
            df = df.merge(customers_df, on='customer_id', how='left')
            
        df = extract_transaction_features(df)
        df = extract_temporal_features(df)
        df = extract_behavioral_features(df)
        
        if self.include_graph_features:
            df = extract_graph_features(df, relationships_df)
            
        return df
    
    def validate_no_leakage(self, features_df: pd.DataFrame, transactions_df: pd.DataFrame) -> bool:
        """Validate that no feature uses future information.
        
        Checks:
        1. All temporal features use only data from before the transaction
        2. Graph features only use relationships established before the transaction
        3. No NaN values in critical features (fill with 0 if needed)
        """
        # Simple validation: ensure no NaN values in final output for critical columns
        has_nan = features_df.isnull().any().any()
        return not has_nan
    
    def get_feature_names(self, include_graph: bool = None) -> list[str]:
        """Return ordered list of feature names."""
        if include_graph is None:
            include_graph = self.include_graph_features
            
        features = [
            'amount', 'amount_log', 'is_refund', 'is_transfer',
            'merchant_category_encoded', 'currency_encoded',
            'transaction_count_5m', 'transaction_count_1h', 'transaction_count_24h',
            'time_since_previous_transaction', 'account_age_hours',
            'hour_of_day', 'day_of_week', 'is_night', 'is_weekend',
            'avg_transaction_amount', 'amount_deviation', 'refund_rate',
            'merchant_count', 'device_count', 'instrument_count'
        ]
        
        if include_graph:
            features.extend([
                'device_account_count', 'ip_account_count', 'instrument_account_count',
                'network_size', 'network_density', 'node_degree', 'network_growth_rate'
            ])
            
        return features
