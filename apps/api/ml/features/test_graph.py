import pandas as pd
import numpy as np
from datetime import datetime, timedelta, timezone
from ml.features.graph import extract_graph_features

def test_empty_relationships():
    transactions_df = pd.DataFrame([
        {'customer_id': 'c1', 'device_id': 'd1', 'ip_id': 'ip1', 'instrument_id': 'inst1', 
         'occurred_at': datetime(2024, 1, 1, 12, tzinfo=timezone.utc)}
    ])
    
    # Missing relationships
    df = extract_graph_features(transactions_df, None)
    assert df.iloc[0]['device_account_count'] == 0.0
    assert df.iloc[0]['network_size'] == 1.0
    assert df.iloc[0]['network_density'] == 0.0
    assert df.iloc[0]['network_growth_rate'] == 0.0

    # Empty relationships
    empty_rels = pd.DataFrame(columns=['source_id', 'target_id', 'source_type', 'target_type', 'first_seen_at'])
    df2 = extract_graph_features(transactions_df, empty_rels)
    assert df2.iloc[0]['device_account_count'] == 0.0

def test_missing_identifiers():
    transactions_df = pd.DataFrame([
        {'customer_id': 'c1', 'device_id': None, 'ip_id': np.nan, 'instrument_id': None, 
         'occurred_at': datetime(2024, 1, 1, 12, tzinfo=timezone.utc)}
    ])
    relationships_df = pd.DataFrame([
        {'source_id': 'c1', 'target_id': 'd1', 'source_type': 'customer', 'target_type': 'device', 
         'first_seen_at': datetime(2024, 1, 1, 10, tzinfo=timezone.utc)}
    ])
    df = extract_graph_features(transactions_df, relationships_df)
    
    assert df.iloc[0]['device_account_count'] == 0.0
    assert df.iloc[0]['ip_account_count'] == 0.0
    assert df.iloc[0]['instrument_account_count'] == 0.0
    assert df.iloc[0]['node_degree'] == 1.0
    assert df.iloc[0]['network_size'] == 2.0

def test_future_leakage():
    t_tx = datetime(2024, 1, 2, 12, tzinfo=timezone.utc)
    transactions_df = pd.DataFrame([
        {'customer_id': 'c1', 'device_id': 'd1', 'occurred_at': t_tx}
    ])
    
    # Relationship appears AFTER the transaction
    relationships_df = pd.DataFrame([
        {'source_id': 'c1', 'target_id': 'd1', 'source_type': 'customer', 'target_type': 'device', 
         'first_seen_at': t_tx + timedelta(hours=1)}
    ])
    
    df = extract_graph_features(transactions_df, relationships_df)
    
    assert df.iloc[0]['device_account_count'] == 0.0
    assert df.iloc[0]['network_size'] == 1.0

def test_shared_device_between_two_customers():
    # c1 and c2 share device d1. 
    # Tx for c2 happens after both are linked to d1.
    relationships_df = pd.DataFrame([
        {'source_id': 'c1', 'target_id': 'd1', 'source_type': 'customer', 'target_type': 'device', 
         'first_seen_at': datetime(2024, 1, 1, 10, tzinfo=timezone.utc)},
        {'source_id': 'c2', 'target_id': 'd1', 'source_type': 'customer', 'target_type': 'device', 
         'first_seen_at': datetime(2024, 1, 1, 11, tzinfo=timezone.utc)}
    ])
    
    transactions_df = pd.DataFrame([
        {'customer_id': 'c2', 'device_id': 'd1', 'occurred_at': datetime(2024, 1, 1, 12, tzinfo=timezone.utc)}
    ])
    
    df = extract_graph_features(transactions_df, relationships_df)
    
    assert df.iloc[0]['device_account_count'] == 2.0
    assert df.iloc[0]['node_degree'] == 1.0
    # network has c1, c2, d1 => 3 nodes
    assert df.iloc[0]['network_size'] == 3.0
    
def test_shared_ip_and_instrument():
    relationships_df = pd.DataFrame([
        {'source_id': 'c1', 'target_id': 'ip1', 'source_type': 'customer', 'target_type': 'ip', 
         'first_seen_at': datetime(2024, 1, 1, 10, tzinfo=timezone.utc)},
        {'source_id': 'c2', 'target_id': 'ip1', 'source_type': 'customer', 'target_type': 'ip', 
         'first_seen_at': datetime(2024, 1, 1, 11, tzinfo=timezone.utc)},
        {'source_id': 'c1', 'target_id': 'inst1', 'source_type': 'customer', 'target_type': 'instrument', 
         'first_seen_at': datetime(2024, 1, 1, 10, tzinfo=timezone.utc)},
    ])
    
    transactions_df = pd.DataFrame([
        {'customer_id': 'c1', 'ip_id': 'ip1', 'instrument_id': 'inst1', 
         'occurred_at': datetime(2024, 1, 1, 12, tzinfo=timezone.utc)}
    ])
    
    df = extract_graph_features(transactions_df, relationships_df)
    assert df.iloc[0]['ip_account_count'] == 2.0
    assert df.iloc[0]['instrument_account_count'] == 1.0

def test_network_density_and_growth():
    # A complete triangle would have density 1.0, but graph is bipartite (customers <-> devices)
    # Let's make a network: c1 - d1, c2 - d1, c2 - d2
    # Nodes: c1, c2, d1, d2 (N=4)
    # Edges: 3
    # Density: 2*3 / (4*3) = 6/12 = 0.5
    
    base_t = datetime(2024, 1, 10, 12, tzinfo=timezone.utc)
    
    relationships_df = pd.DataFrame([
        {'source_id': 'c1', 'target_id': 'd1', 'source_type': 'customer', 'target_type': 'device', 
         'first_seen_at': base_t - timedelta(days=10)},  # 10 days ago (old)
        {'source_id': 'c2', 'target_id': 'd1', 'source_type': 'customer', 'target_type': 'device', 
         'first_seen_at': base_t - timedelta(days=3)},   # 3 days ago (new)
        {'source_id': 'c2', 'target_id': 'd2', 'source_type': 'customer', 'target_type': 'device', 
         'first_seen_at': base_t - timedelta(days=1)},   # 1 day ago (new)
    ])
    
    transactions_df = pd.DataFrame([
        {'customer_id': 'c1', 'occurred_at': base_t}
    ])
    
    df = extract_graph_features(transactions_df, relationships_df)
    
    assert df.iloc[0]['network_size'] == 4.0
    assert df.iloc[0]['network_density'] == 0.5
    
    # Growth rate: nodes added in last 7 days are c2 (3 days ago), d2 (1 day ago).
    # d1 and c1 were added 10 days ago.
    # Total new nodes = 2
    # Rate = 2 / 7.0
    assert np.isclose(df.iloc[0]['network_growth_rate'], 2.0 / 7.0)
