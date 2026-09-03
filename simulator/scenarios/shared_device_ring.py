import uuid
import random
from datetime import datetime, timedelta

class SharedDeviceRingScenario:
    """5-15 accounts sharing 1-2 devices, coordinated timing."""
    
    def generate(self, customers, merchants, devices, instruments, ips, config) -> tuple[list[dict], list[dict]]:
        transactions = []
        ground_truth = []
        
        for i in range(config.num_shared_device_rings):
            scenario_id = f'shared_device_ring_{i}'
            ring_size = random.randint(*config.ring_size_range)
            ring_customers = random.sample(customers, min(ring_size, len(customers)))
            shared_devices = random.sample(devices, random.randint(1, 2))
            shared_ips = random.sample(ips, random.randint(1, 2))
            target_merchants = random.sample(merchants, random.randint(1, 3))
            
            days_range = (config.end_date - config.start_date).days
            burst_start = config.start_date + timedelta(days=random.randint(0, max(1, days_range-1)), hours=random.randint(0, 23))
            
            for c in ring_customers:
                ground_truth.append({
                    'entity_type': 'customer',
                    'entity_id': c['customer_id'],
                    'scenario_id': scenario_id,
                    'is_abuse': True,
                    'abuse_type': 'shared_device_ring',
                    'injected_at': datetime.utcnow()
                })
                
                tx_time = burst_start + timedelta(minutes=random.randint(0, 120))
                tx = {
                    'transaction_id': str(uuid.uuid4()),
                    'customer_id': c['customer_id'],
                    'merchant_id': random.choice(target_merchants)['merchant_id'],
                    'device_id': random.choice(shared_devices)['device_id'],
                    'instrument_id': random.choice(instruments)['instrument_id'],
                    'ip_id': random.choice(shared_ips)['ip_id'],
                    'amount': round(random.uniform(50, 150), 2),
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
                    'abuse_type': 'shared_device_ring',
                    'injected_at': datetime.utcnow()
                })
                
        return transactions, ground_truth
