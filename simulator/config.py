from dataclasses import dataclass, field
from datetime import datetime, timedelta

@dataclass
class SimulationConfig:
    # Entity counts
    num_customers: int = 1000
    num_merchants: int = 200
    num_devices: int = 500
    num_instruments: int = 800
    num_ips: int = 600
    
    # Transaction generation
    num_normal_transactions: int = 50000
    
    # Time range
    start_date: datetime = field(default_factory=lambda: datetime(2024, 1, 1))
    end_date: datetime = field(default_factory=lambda: datetime(2024, 6, 30))
    
    # Abuse scenario counts
    num_shared_device_rings: int = 5
    num_velocity_abusers: int = 10
    num_account_farms: int = 3
    num_refund_abusers: int = 8
    num_network_expansions: int = 4
    
    # Abuse scenario sizes
    ring_size_range: tuple = (5, 15)
    farm_size_range: tuple = (10, 30)
    
    # Countries
    countries: list = field(default_factory=lambda: ['US', 'GB', 'IN', 'DE', 'FR', 'JP', 'BR', 'AU'])
    currencies: list = field(default_factory=lambda: ['USD', 'GBP', 'INR', 'EUR', 'JPY', 'BRL', 'AUD'])
    device_types: list = field(default_factory=lambda: ['mobile_android', 'mobile_ios', 'desktop_windows', 'desktop_mac', 'tablet'])
    instrument_types: list = field(default_factory=lambda: ['credit_card', 'debit_card', 'upi', 'bank_transfer', 'wallet'])
    merchant_categories: list = field(default_factory=lambda: ['grocery', 'electronics', 'clothing', 'food_delivery', 'gaming', 'travel', 'subscription', 'marketplace', 'utility', 'pharmacy'])
    transaction_types: list = field(default_factory=lambda: ['purchase', 'refund', 'transfer', 'withdrawal'])
    
    # Random seed
    seed: int = 42
