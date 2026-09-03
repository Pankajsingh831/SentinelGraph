import uuid
import random
import numpy as np
from datetime import datetime, timedelta

class NormalScenario:
    """Generates realistic normal transaction patterns."""
    
    def generate(self, customers, merchants, devices, instruments, ips, config) -> tuple[list[dict], list[dict]]:
        transactions = []
        ground_truth = []
        
        customer_prefs = {}
        for c in customers:
            customer_prefs[c['customer_id']] = {
                'merchants': random.sample(merchants, random.randint(1, 3)),
                'devices': random.sample(devices, random.randint(1, 2)),
                'instruments': random.sample(instruments, random.randint(1, 3)),
                'ips': random.sample(ips, random.randint(1, 2))
            }
        
        start_ts = config.start_date.timestamp()
        end_ts = config.end_date.timestamp()
        
        for _ in range(config.num_normal_transactions):
            c = random.choice(customers)
            prefs = customer_prefs[c['customer_id']]
            
            m = random.choice(prefs['merchants'])
            d = random.choice(prefs['devices'])
            inst = random.choice(prefs['instruments'])
            ip = random.choice(prefs['ips'])
            
            amount = np.random.lognormal(mean=np.log(50), sigma=1.0)
            amount = min(round(float(amount), 2), 5000.0)
            
            t = random.uniform(start_ts, end_ts)
            occurred_at = datetime.fromtimestamp(t)
            
            tx_type = random.choices(
                ['purchase', 'transfer', 'refund'], 
                weights=[0.85, 0.10, 0.05], 
                k=1
            )[0]
            
            tx = {
                'transaction_id': str(uuid.uuid4()),
                'customer_id': c['customer_id'],
                'merchant_id': m['merchant_id'],
                'device_id': d['device_id'],
                'instrument_id': inst['instrument_id'],
                'ip_id': ip['ip_id'],
                'amount': amount,
                'currency': random.choice(config.currencies),
                'transaction_type': tx_type,
                'status': 'completed',
                'occurred_at': occurred_at,
                'created_at': datetime.utcnow()
            }
            transactions.append(tx)
            
            ground_truth.append({
                'entity_type': 'transaction',
                'entity_id': tx['transaction_id'],
                'scenario_id': 'normal',
                'is_abuse': False,
                'abuse_type': None,
                'injected_at': datetime.utcnow()
            })
            
        return transactions, ground_truth
