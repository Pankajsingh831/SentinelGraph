import uuid
import random
from datetime import datetime, timedelta

class VelocityAbuseScenario:
    """Single account with extreme transaction velocity spikes."""
    
    def generate(self, customers, merchants, devices, instruments, ips, config) -> tuple[list[dict], list[dict]]:
        transactions = []
        ground_truth = []
        
        for i in range(config.num_velocity_abusers):
            scenario_id = f'velocity_abuse_{i}'
            customer = random.choice(customers)
            d = random.choice(devices)
            inst = random.choice(instruments)
            ip = random.choice(ips)
            target_merchant = random.choice(merchants)
            
            days_range = (config.end_date - config.start_date).days
            burst_start = config.start_date + timedelta(days=random.randint(0, max(1, days_range-1)), hours=random.randint(0, 23))
            
            num_txs = random.randint(20, 50)
            
            ground_truth.append({
                'entity_type': 'customer',
                'entity_id': customer['customer_id'],
                'scenario_id': scenario_id,
                'is_abuse': True,
                'abuse_type': 'velocity_abuse',
                'injected_at': datetime.utcnow()
            })
            
            for _ in range(num_txs):
                tx_time = burst_start + timedelta(seconds=random.randint(0, 300))
                tx = {
                    'transaction_id': str(uuid.uuid4()),
                    'customer_id': customer['customer_id'],
                    'merchant_id': target_merchant['merchant_id'],
                    'device_id': d['device_id'],
                    'instrument_id': inst['instrument_id'],
                    'ip_id': ip['ip_id'],
                    'amount': round(random.uniform(1.0, 5.0), 2),
                    'currency': random.choice(config.currencies),
                    'transaction_type': 'purchase',
                    'status': 'completed',
                    'occurred_at': tx_time,
                    'created_at': datetime.utcnow()
                }
                transactions.append(tx)
                
                ground_truth.append({
                    'entity_type': 'transaction',
                    'entity_id': tx['transaction_id'],
                    'scenario_id': scenario_id,
                    'is_abuse': True,
                    'abuse_type': 'velocity_abuse',
                    'injected_at': datetime.utcnow()
                })
                
        return transactions, ground_truth
