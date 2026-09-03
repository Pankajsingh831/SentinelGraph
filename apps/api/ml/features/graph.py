import pandas as pd
import numpy as np
from collections import defaultdict

def extract_graph_features(transactions_df: pd.DataFrame, relationships_df: pd.DataFrame = None) -> pd.DataFrame:
    """
    Extract graph/network features per transaction safely with NO future leakage.
    
    Features:
    - device_account_count: distinct customers connected to the transaction's device up to T
    - ip_account_count: distinct customers connected to the transaction's IP up to T
    - instrument_account_count: distinct customers connected to the transaction's instrument up to T
    - network_size: number of connected entities in the customer's component up to T
    - network_density: 2E / (N(N-1)) of the customer's component up to T (0.0 if N < 2)
    - node_degree: number of distinct entities connected to the customer up to T
    - network_growth_rate: new nodes added to the customer's component in the 7 days prior to T, divided by 7.
    """
    df = transactions_df.copy()
    if df.empty:
        for col in ['device_account_count', 'ip_account_count', 'instrument_account_count', 
                    'network_size', 'network_density', 'node_degree', 'network_growth_rate']:
            df[col] = 0.0
        return df

    # Ensure occurred_at is tz-aware
    df['occurred_at'] = pd.to_datetime(df['occurred_at'], utc=True)
    df = df.sort_values('occurred_at').reset_index(drop=False)
    
    N = len(df)
    device_account_count = np.zeros(N, dtype=float)
    ip_account_count = np.zeros(N, dtype=float)
    instrument_account_count = np.zeros(N, dtype=float)
    network_size = np.zeros(N, dtype=float)
    network_density = np.zeros(N, dtype=float)
    node_degree = np.zeros(N, dtype=float)
    network_growth_rate = np.zeros(N, dtype=float)

    valid_rels = False
    if relationships_df is not None and not relationships_df.empty:
        req_cols = {'source_id', 'target_id', 'source_type', 'target_type', 'first_seen_at'}
        if req_cols.issubset(relationships_df.columns):
            valid_rels = True
            
    if valid_rels:
        rels = relationships_df.copy()
        rels['first_seen_at'] = pd.to_datetime(rels['first_seen_at'], utc=True)
        rels = rels.sort_values('first_seen_at')
        rels_list = rels.to_dict('records')
    else:
        rels_list = []

    # State
    device_customers = defaultdict(set)
    ip_customers = defaultdict(set)
    instrument_customers = defaultdict(set)
    adj = defaultdict(set)
    node_first_seen = {}
    
    import bisect

    # DSU
    parent = {}
    size = {}
    edges_count = {}
    comp_timestamps = defaultdict(list)

    def find(i):
        if parent[i] == i:
            return i
        parent[i] = find(parent[i])
        return parent[i]

    def add_node(u, t):
        if u not in parent:
            parent[u] = u
            size[u] = 1
            edges_count[u] = 0
            node_first_seen[u] = t
            comp_timestamps[u].append(t)

    def union(u, v, t):
        add_node(u, t)
        add_node(v, t)
        
        if t < node_first_seen[u]: node_first_seen[u] = t
        if t < node_first_seen[v]: node_first_seen[v] = t

        root_u = find(u)
        root_v = find(v)
        if root_u != root_v:
            if size[root_u] < size[root_v]:
                root_u, root_v = root_v, root_u
                
            parent[root_v] = root_u
            size[root_u] += size[root_v]
            edges_count[root_u] += edges_count[root_v] + 1
            comp_timestamps[root_u].extend(comp_timestamps[root_v])
            comp_timestamps[root_u].sort()
            comp_timestamps.pop(root_v, None)
        else:
            edges_count[root_u] += 1

    rel_idx = 0
    num_rels = len(rels_list)

    occurred_at_vals = df['occurred_at'].tolist()
    customer_id_vals = df['customer_id'].tolist() if 'customer_id' in df else [None] * N
    
    device_id_col = 'device_id' if 'device_id' in df else None
    ip_id_col = 'ip_id' if 'ip_id' in df else 'ip_address' if 'ip_address' in df else None
    inst_id_col = 'instrument_id' if 'instrument_id' in df else None

    device_id_vals = df[device_id_col].tolist() if device_id_col else [None] * N
    ip_id_vals = df[ip_id_col].tolist() if ip_id_col else [None] * N
    inst_id_vals = df[inst_id_col].tolist() if inst_id_col else [None] * N

    for i in range(N):
        t = occurred_at_vals[i]
        c = str(customer_id_vals[i]) if pd.notnull(customer_id_vals[i]) else None
        d = str(device_id_vals[i]) if pd.notnull(device_id_vals[i]) else None
        ip = str(ip_id_vals[i]) if pd.notnull(ip_id_vals[i]) else None
        inst = str(inst_id_vals[i]) if pd.notnull(inst_id_vals[i]) else None
        
        while rel_idx < num_rels and rels_list[rel_idx]['first_seen_at'] <= t:
            r = rels_list[rel_idx]
            u = str(r['source_id']) if pd.notnull(r['source_id']) else None
            v = str(r['target_id']) if pd.notnull(r['target_id']) else None
            type_u, type_v = r['source_type'], r['target_type']
            rt = r['first_seen_at']
            
            if u is not None and v is not None and v not in adj[u]:
                adj[u].add(v)
                adj[v].add(u)
                
                def update_counts(n1, t1, n2, t2):
                    if t1 == 'customer':
                        if t2 == 'device':
                            device_customers[n2].add(n1)
                        elif t2 in ('ip', 'ip_address', 'ip_id'):
                            ip_customers[n2].add(n1)
                        elif t2 in ('instrument', 'payment_instrument', 'instrument_id'):
                            instrument_customers[n2].add(n1)
                            
                update_counts(u, type_u, v, type_v)
                update_counts(v, type_v, u, type_u)
                union(u, v, rt)
            
            rel_idx += 1

        device_account_count[i] = len(device_customers.get(d, set())) if d is not None else 0.0
        ip_account_count[i] = len(ip_customers.get(ip, set())) if ip is not None else 0.0
        instrument_account_count[i] = len(instrument_customers.get(inst, set())) if inst is not None else 0.0
        
        node_degree[i] = len(adj[c]) if c is not None and c in adj else 0.0
        
        if c is not None and c in parent:
            root = find(c)
            n_size = size[root]
            network_size[i] = n_size
            
            if n_size > 1:
                e_count = edges_count[root]
                network_density[i] = (2.0 * e_count) / (n_size * (n_size - 1))
            else:
                network_density[i] = 0.0
                
            seven_days_ago = t - pd.Timedelta(days=7)
            ts_list = comp_timestamps[root]
            idx = bisect.bisect_left(ts_list, seven_days_ago)
            new_nodes = len(ts_list) - idx
            network_growth_rate[i] = new_nodes / 7.0
        else:
            network_size[i] = 1.0
            network_density[i] = 0.0
            network_growth_rate[i] = 0.0

    df['device_account_count'] = device_account_count
    df['ip_account_count'] = ip_account_count
    df['instrument_account_count'] = instrument_account_count
    df['network_size'] = network_size
    df['network_density'] = network_density
    df['node_degree'] = node_degree
    df['network_growth_rate'] = network_growth_rate

    return df.set_index('index').sort_index()
