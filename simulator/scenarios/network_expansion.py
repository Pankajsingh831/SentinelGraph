import uuid
import random
from datetime import datetime, timedelta

class NetworkExpansionScenario:
    """Gradually growing network of connected accounts."""
    
    def generate(self, customers, merchants, devices, instruments, ips, config) -> tuple[list[dict], list[dict]]:
        transactions = []
        ground_truth = []
        
        for i in range(config.num_network_expansions):
            scenario_id = f'network_expansion_{i}'
            
            start_date = config.start_date + timedelta(days=random.randint(0, 30))
            
            network_customers = random.sample(customers, random.randint(2, 3))
            network_devices = random.sample(devices, 1)
            network_ips = random.sample(ips, 1)
            
            target_merchant = random.choice(merchants)
            
            for step in range(4): # Grow over 4 weeks
                current_date = start_date + timedelta(days=step*7)
                
                network_customers.extend(random.sample(customers, random.randint(1, 3)))
                network_devices.extend(random.sample(devices, random.randint(0, 1)))
                network_ips.extend(random.sample(ips, random.randint(0, 1)))
                
                for c in network_customers:
                    ground_truth.append({
                        'entity_type': 'customer',
                        'entity_id': c['customer_id'],
                        'scenario_id': scenario_id,
                        'is_abuse': True,
                        'abuse_type': 'network_expansion',
                        'injected_at': datetime.utcnow()
                    })
                    
                    tx = {
                        'transaction_id': str(uuid.uuid4()),
                        'customer_id': c['customer_id'],
                        'merchant_id': target_merchant['merchant_id'],
                        'device_id': random.choice(network_devices)['device_id'],
                        'instrument_id': random.choice(instruments)['instrument_id'],
                        'ip_id': random.choice(network_ips)['ip_id'],
                        'amount': round(random.uniform(20.0, 80.0), 2),
                        'currency': random.choice(config.currencies),
                        'transaction_type': 'purchase',
                        'status': 'completed',
                        'occurred_at': current_date + timedelta(hours=random.randint(0, 23)),
                        'created_at': datetime.utcnow()
                    }
                    transactions.append(tx)
                    ground_truth.append({
                        'entity_type': 'transaction',
                        'entity_id': tx['transaction_id'],
                        'scenario_id': scenario_id,
                        'is_abuse': True,
                        'abuse_type': 'network_expansion',
                        'injected_at': datetime.utcnow()
                    })
                    
        return transactions, ground_truth
