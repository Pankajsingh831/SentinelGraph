import uuid
import random
import hashlib
from datetime import datetime, timedelta
from typing import List, Dict
from .config import SimulationConfig

def generate_customers(config: SimulationConfig) -> List[Dict]:
    customers = []
    days_range = (config.end_date - config.start_date).days
    for _ in range(config.num_customers):
        offset = int(random.triangular(0, days_range, 0))
        created_at = config.start_date + timedelta(days=offset)
        customers.append({
            'customer_id': str(uuid.uuid4()),
            'status': 'active',
            'country': random.choice(config.countries),
            'account_created_at': created_at,
            'created_at': datetime.utcnow()
        })
    return customers

def generate_merchants(config: SimulationConfig) -> List[Dict]:
    merchants = []
    for i in range(config.num_merchants):
        category = random.choice(config.merchant_categories)
        merchants.append({
            'merchant_id': str(uuid.uuid4()),
            'merchant_name': f"{category.capitalize()} Store {i}",
            'category': category,
            'country': random.choice(config.countries),
            'status': 'active',
            'created_at': datetime.utcnow()
        })
    return merchants

def generate_devices(config: SimulationConfig) -> List[Dict]:
    devices = []
    for _ in range(config.num_devices):
        devices.append({
            'device_id': str(uuid.uuid4()),
            'device_type': random.choice(config.device_types),
            'first_seen_at': config.start_date,
            'last_seen_at': config.end_date
        })
    return devices

def generate_payment_instruments(config: SimulationConfig) -> List[Dict]:
    instruments = []
    for _ in range(config.num_instruments):
        instruments.append({
            'instrument_id': str(uuid.uuid4()),
            'instrument_type': random.choice(config.instrument_types),
            'issuer_country': random.choice(config.countries),
            'first_seen_at': config.start_date,
            'last_seen_at': config.end_date
        })
    return instruments

def generate_ip_addresses(config: SimulationConfig) -> List[Dict]:
    ips = []
    for _ in range(config.num_ips):
        fake_ip = f"{random.randint(1, 255)}.{random.randint(0, 255)}.{random.randint(0, 255)}.{random.randint(0, 255)}"
        ip_hash = hashlib.sha256(fake_ip.encode()).hexdigest()
        ips.append({
            'ip_id': str(uuid.uuid4()),
            'ip_hash': ip_hash,
            'country': random.choice(config.countries),
            'first_seen_at': config.start_date,
            'last_seen_at': config.end_date
        })
    return ips
