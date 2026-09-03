import uuid
import random
from datetime import datetime, timedelta

class AccountFarmingScenario:
    """Batch account creation from shared IPs/devices, minimal activity."""
    
    def generate(self, customers, merchants, devices, instruments, ips, config) -> tuple[list[dict], list[dict]]:
        transactions = []
        ground_truth = []
        
        for i in range(config.num_account_farms):
            scenario_id = f'account_farming_{i}'
            farm_size = random.randint(*config.farm_size_range)
            shared_devices = random.sample(devices, random.randint(1, 2))
            shared_ips = random.sample(ips, random.randint(1, 3))
            
            days_range = (config.end_date - config.start_date).days
            farm_start = config.start_date + timedelta(days=random.randint(0, max(1, days_range-1)))
            farm_customers = random.sample(customers, min(farm_size, len(customers)))
            
            for c in farm_customers:
                c_id = c['customer_id']
                
                ground_truth.append({
                    'entity_type': 'customer',
                    'entity_id': c_id,
                    'scenario_id': scenario_id,
                    'is_abuse': True,
                    'abuse_type': 'account_farming',
                    'injected_at': datetime.utcnow()
                })
                
                for _ in range(random.randint(1, 3)):
                    tx_time = farm_start + timedelta(hours=random.randint(0, 48))
                    tx = {
                        'transaction_id': str(uuid.uuid4()),
                        'customer_id': c_id,
                        'merchant_id': random.choice(merchants)['merchant_id'],
                        'device_id': random.choice(shared_devices)['device_id'],
                        'instrument_id': random.choice(instruments)['instrument_id'],
                        'ip_id': random.choice(shared_ips)['ip_id'],
                        'amount': round(random.uniform(5.0, 20.0), 2),
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
                        'abuse_type': 'account_farming',
                        'injected_at': datetime.utcnow()
                    })
                    
        return transactions, ground_truth
