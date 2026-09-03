import uuid
import random
from datetime import datetime, timedelta

class RefundAbuseScenario:
    """High refund rate from related accounts."""
    
    def generate(self, customers, merchants, devices, instruments, ips, config) -> tuple[list[dict], list[dict]]:
        transactions = []
        ground_truth = []
        
        for i in range(config.num_refund_abusers):
            scenario_id = f'refund_abuse_{i}'
            abuse_customers = random.sample(customers, random.randint(3, 5))
            shared_devices = random.sample(devices, random.randint(1, 2))
            shared_ips = random.sample(ips, random.randint(1, 2))
            target_merchant = random.choice(merchants)
            
            for c in abuse_customers:
                ground_truth.append({
                    'entity_type': 'customer',
                    'entity_id': c['customer_id'],
                    'scenario_id': scenario_id,
                    'is_abuse': True,
                    'abuse_type': 'refund_abuse',
                    'injected_at': datetime.utcnow()
                })
                
                days_range = (config.end_date - config.start_date).days
                tx_date = config.start_date + timedelta(days=random.randint(0, max(1, days_range-5)))
                
                amount = round(random.uniform(100.0, 500.0), 2)
                d = random.choice(shared_devices)
                ip = random.choice(shared_ips)
                inst = random.choice(instruments)
                
                tx_purchase = {
                    'transaction_id': str(uuid.uuid4()),
                    'customer_id': c['customer_id'],
                    'merchant_id': target_merchant['merchant_id'],
                    'device_id': d['device_id'],
                    'instrument_id': inst['instrument_id'],
                    'ip_id': ip['ip_id'],
                    'amount': amount,
                    'currency': random.choice(config.currencies),
                    'transaction_type': 'purchase',
                    'status': 'completed',
                    'occurred_at': tx_date,
                    'created_at': datetime.utcnow()
                }
                transactions.append(tx_purchase)
                ground_truth.append({
                    'entity_type': 'transaction',
                    'entity_id': tx_purchase['transaction_id'],
                    'scenario_id': scenario_id,
                    'is_abuse': True,
                    'abuse_type': 'refund_abuse',
                    'injected_at': datetime.utcnow()
                })
                
                tx_refund = {
                    'transaction_id': str(uuid.uuid4()),
                    'customer_id': c['customer_id'],
                    'merchant_id': target_merchant['merchant_id'],
                    'device_id': d['device_id'],
                    'instrument_id': inst['instrument_id'],
                    'ip_id': ip['ip_id'],
                    'amount': amount,
                    'currency': tx_purchase['currency'],
                    'transaction_type': 'refund',
                    'status': 'completed',
                    'occurred_at': tx_date + timedelta(days=random.randint(1, 3)),
                    'created_at': datetime.utcnow()
                }
                transactions.append(tx_refund)
                ground_truth.append({
                    'entity_type': 'transaction',
                    'entity_id': tx_refund['transaction_id'],
                    'scenario_id': scenario_id,
                    'is_abuse': True,
                    'abuse_type': 'refund_abuse',
                    'injected_at': datetime.utcnow()
                })
                
        return transactions, ground_truth
