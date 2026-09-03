import pytest
import numpy as np
import pandas as pd
from datetime import datetime, timedelta, timezone

from ml.features.graph import extract_graph_features


def test_task2_current_event_self_contribution():
    """Task 2: Audit behavior when relationship first appears at exactly the transaction time."""
    t1 = datetime(2024, 1, 1, 10, 0, 0, tzinfo=timezone.utc)
    t2 = datetime(2024, 1, 1, 11, 0, 0, tzinfo=timezone.utc)
    
    # Customer A, Device X, Tx T1 at 10:00:00
    # Relationship (A, X) first appears at exactly 10:00:00
    # Customer B, Device X, Tx T2 at 11:00:00
    # Relationship (B, X) first appears at exactly 11:00:00
    transactions_df = pd.DataFrame([
        {'transaction_id': 't1', 'customer_id': 'cust_A', 'device_id': 'dev_X', 'occurred_at': t1},
        {'transaction_id': 't2', 'customer_id': 'cust_B', 'device_id': 'dev_X', 'occurred_at': t2}
    ])
    
    relationships_df = pd.DataFrame([
        {'source_id': 'cust_A', 'target_id': 'dev_X', 'source_type': 'customer', 'target_type': 'device', 'first_seen_at': t1},
        {'source_id': 'cust_B', 'target_id': 'dev_X', 'source_type': 'customer', 'target_type': 'device', 'first_seen_at': t2}
    ])
    
    df = extract_graph_features(transactions_df, relationships_df)
    
    row_t1 = df[df['transaction_id'] == 't1'].iloc[0]
    row_t2 = df[df['transaction_id'] == 't2'].iloc[0]
    
    # At T1 (10:00:00):
    # Customer A transacts on Device X.
    # The (A, X) relationship is active at 10:00:00 (first_seen_at <= t1).
    # Device X is connected to Customer A -> device_account_count = 1.0
    # Component has {cust_A, dev_X} -> network_size = 2.0
    # 1 edge between 2 nodes -> network_density = 2*1 / (2*1) = 1.0
    # Node degree for cust_A -> 1.0
    # Growth rate: 2 nodes added in last 7 days -> 2 / 7.0
    assert row_t1['device_account_count'] == 1.0
    assert row_t1['network_size'] == 2.0
    assert row_t1['network_density'] == 1.0
    assert row_t1['node_degree'] == 1.0
    assert np.isclose(row_t1['network_growth_rate'], 2.0 / 7.0)
    
    # At T2 (11:00:00):
    # Customer B transacts on Device X.
    # Historical relationship (cust_A, dev_X) + current relationship (cust_B, dev_X) are active.
    # Device X is connected to cust_A and cust_B -> device_account_count = 2.0
    # Component has {cust_A, cust_B, dev_X} -> network_size = 3.0
    # 2 edges between 3 nodes -> network_density = 2*2 / (3*2) = 4/6 = 0.6667
    # Node degree for cust_B -> 1.0
    # Growth rate: 3 nodes added in last 7 days -> 3 / 7.0
    assert row_t2['device_account_count'] == 2.0
    assert row_t2['network_size'] == 3.0
    assert np.isclose(row_t2['network_density'], 2.0 / 3.0)
    assert row_t2['node_degree'] == 1.0
    assert np.isclose(row_t2['network_growth_rate'], 3.0 / 7.0)


def test_task3_future_leakage_strict_isolation():
    """Task 3: Verify that NO relationship, node, or edge with first_seen_at > T affects T."""
    t_target = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    
    transactions_df = pd.DataFrame([
        {'transaction_id': 't_curr', 'customer_id': 'c1', 'device_id': 'd1', 'occurred_at': t_target},
        {'transaction_id': 't_future', 'customer_id': 'c2', 'device_id': 'd1', 'occurred_at': t_target + timedelta(hours=2)}
    ])
    
    # c1-d1 exists before T
    # c2-d1 (linking c2 to the same device) only exists AFTER T (at T + 1 hour)
    # c3-d2 exists only AFTER T
    relationships_df = pd.DataFrame([
        {'source_id': 'c1', 'target_id': 'd1', 'source_type': 'customer', 'target_type': 'device', 
         'first_seen_at': t_target - timedelta(hours=1)},
        {'source_id': 'c2', 'target_id': 'd1', 'source_type': 'customer', 'target_type': 'device', 
         'first_seen_at': t_target + timedelta(hours=1)}, # FUTURE relative to t_curr
        {'source_id': 'c3', 'target_id': 'd2', 'source_type': 'customer', 'target_type': 'device', 
         'first_seen_at': t_target + timedelta(hours=5)}  # FUTURE relative to all
    ])
    
    df = extract_graph_features(transactions_df, relationships_df)
    row_curr = df[df['transaction_id'] == 't_curr'].iloc[0]
    
    # At T:
    # c2-d1 MUST NOT contribute to c1's transaction at T!
    # device_account_count for d1 at T must be 1.0 (only c1), NOT 2.0
    assert row_curr['device_account_count'] == 1.0
    # network_size for c1 at T must be 2.0 (c1, d1), NOT 3.0 (c1, c2, d1)
    assert row_curr['network_size'] == 2.0
    # node_degree for c1 is 1.0
    assert row_curr['node_degree'] == 1.0
    
    # At T + 2 hours:
    row_future = df[df['transaction_id'] == 't_future'].iloc[0]
    # Now c2-d1 has arrived (first_seen at T+1 <= T+2), so d1 has 2 accounts
    assert row_future['device_account_count'] == 2.0
    assert row_future['network_size'] == 3.0


def test_task4_network_growth_rate_semantics():
    """Task 4: Audit 7-day window boundary, node-first-seen semantics, and DSU merge preservation."""
    t = datetime(2024, 1, 15, 12, 0, 0, tzinfo=timezone.utc)
    
    # Nodes:
    # c1 and d1: first seen 10 days ago (outside 7-day window)
    # c2 and d2: first seen exactly 7 days ago (boundary: t - 7 days) -> included
    # c3: first seen 3 days ago -> included
    # c4: first seen 1 day ago -> included
    # c5: outside c1's component -> MUST NOT be included in c1's growth rate!
    relationships_df = pd.DataFrame([
        # Component 1 (old core):
        {'source_id': 'c1', 'target_id': 'd1', 'source_type': 'customer', 'target_type': 'device',
         'first_seen_at': t - timedelta(days=10)},
        # Component 2 (merged into Component 1 via d1):
        {'source_id': 'c2', 'target_id': 'd1', 'source_type': 'customer', 'target_type': 'device',
         'first_seen_at': t - timedelta(days=7)}, # exact 7 day boundary
        {'source_id': 'c2', 'target_id': 'd2', 'source_type': 'customer', 'target_type': 'device',
         'first_seen_at': t - timedelta(days=7)},
        {'source_id': 'c3', 'target_id': 'd2', 'source_type': 'customer', 'target_type': 'device',
         'first_seen_at': t - timedelta(days=3)},
        {'source_id': 'c4', 'target_id': 'd2', 'source_type': 'customer', 'target_type': 'device',
         'first_seen_at': t - timedelta(days=1)},
        # Component 3 (DISCONNECTED from c1):
        {'source_id': 'c5', 'target_id': 'd5', 'source_type': 'customer', 'target_type': 'device',
         'first_seen_at': t - timedelta(days=1)}
    ])
    
    transactions_df = pd.DataFrame([
        {'transaction_id': 'tx_c1', 'customer_id': 'c1', 'occurred_at': t}
    ])
    
    df = extract_graph_features(transactions_df, relationships_df)
    row = df.iloc[0]
    
    # In c1's component:
    # Nodes: c1, d1, c2, d2, c3, c4 (6 nodes)
    # c5 and d5 are NOT in c1's component!
    assert row['network_size'] == 6.0
    
    # Nodes added in last 7 days (first_seen >= t - 7 days):
    # c1: 10 days ago (NO)
    # d1: 10 days ago (NO)
    # c2: 7 days ago (YES, at boundary)
    # d2: 7 days ago (YES, at boundary)
    # c3: 3 days ago (YES)
    # c4: 1 day ago (YES)
    # Total new nodes in component = 4
    # Expected growth rate = 4 / 7.0
    assert np.isclose(row['network_growth_rate'], 4.0 / 7.0)


def test_task5_network_density_and_duplicate_relationships():
    """Task 5: Verify that duplicate relationships or repeated interactions DO NOT inflate edges/density."""
    t = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    
    # 3 nodes: c1, d1, c2 (simple path: c1 - d1 - c2)
    # Total distinct edges: 2
    # Theoretical maximum edges: 3 * 2 / 2 = 3
    # Density = 2 * 2 / (3 * 2) = 4 / 6 = 0.6667
    
    # Suppose the same relationship (c1, d1) appears multiple times (repeated transactions or multi-edges)
    relationships_df = pd.DataFrame([
        {'source_id': 'c1', 'target_id': 'd1', 'source_type': 'customer', 'target_type': 'device', 'first_seen_at': t - timedelta(hours=5)},
        {'source_id': 'c1', 'target_id': 'd1', 'source_type': 'customer', 'target_type': 'device', 'first_seen_at': t - timedelta(hours=4)}, # duplicate edge!
        {'source_id': 'd1', 'target_id': 'c1', 'source_type': 'device', 'target_type': 'customer', 'first_seen_at': t - timedelta(hours=3)}, # reverse duplicate edge!
        {'source_id': 'c2', 'target_id': 'd1', 'source_type': 'customer', 'target_type': 'device', 'first_seen_at': t - timedelta(hours=2)},
        {'source_id': 'c2', 'target_id': 'd1', 'source_type': 'customer', 'target_type': 'device', 'first_seen_at': t - timedelta(hours=1)}, # duplicate edge!
    ])
    
    transactions_df = pd.DataFrame([
        {'customer_id': 'c1', 'device_id': 'd1', 'occurred_at': t}
    ])
    
    df = extract_graph_features(transactions_df, relationships_df)
    row = df.iloc[0]
    
    assert row['network_size'] == 3.0
    assert row['node_degree'] == 1.0 # only d1 connected to c1
    # Density must be 2 / 3 = 0.6667, NOT inflated above 1.0 by duplicate edges!
    assert np.isclose(row['network_density'], 2.0 / 3.0)
    assert 0.0 <= row['network_density'] <= 1.0
