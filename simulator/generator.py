import argparse
import asyncio
import os
import random
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path
import numpy as np

# Controlled import-path adjustment:
# Ensure apps/api is accessible on sys.path so the simulator can resolve app.models
# even if generator.py is executed directly as a standalone script.
_REPO_ROOT = Path(__file__).resolve().parent.parent
_API_DIR = _REPO_ROOT / "apps" / "api"
if _API_DIR.is_dir() and str(_API_DIR) not in sys.path:
    sys.path.insert(0, str(_API_DIR))

if __package__ is None or __package__ == '':
    if str(_REPO_ROOT) not in sys.path:
        sys.path.insert(0, str(_REPO_ROOT))
    from simulator.config import SimulationConfig
    from simulator.entities import (
        generate_customers,
        generate_merchants,
        generate_devices,
        generate_payment_instruments,
        generate_ip_addresses
    )
    from simulator.scenarios import (
        NormalScenario,
        SharedDeviceRingScenario,
        VelocityAbuseScenario,
        AccountFarmingScenario,
        RefundAbuseScenario,
        NetworkExpansionScenario
    )
else:
    from .config import SimulationConfig
    from .entities import (
        generate_customers,
        generate_merchants,
        generate_devices,
        generate_payment_instruments,
        generate_ip_addresses
    )
    from .scenarios import (
        NormalScenario,
        SharedDeviceRingScenario,
        VelocityAbuseScenario,
        AccountFarmingScenario,
        RefundAbuseScenario,
        NetworkExpansionScenario
    )

class DataGenerator:
    def __init__(self, config: SimulationConfig = None):
        self.config = config or SimulationConfig()
        random.seed(self.config.seed)
        np.random.seed(self.config.seed)
    
    async def generate_all(self, db_url: str = None):
        """Generate all entities, normal transactions, and abuse scenarios."""
        print("Generating entities...")
        customers = generate_customers(self.config)
        merchants = generate_merchants(self.config)
        devices = generate_devices(self.config)
        instruments = generate_payment_instruments(self.config)
        ips = generate_ip_addresses(self.config)
        
        entities = {
            'customers': customers,
            'merchants': merchants,
            'devices': devices,
            'instruments': instruments,
            'ips': ips
        }
        
        all_transactions = []
        all_ground_truth = []
        
        print("Generating normal transactions...")
        normal_gen = NormalScenario()
        tx, gt = normal_gen.generate(customers, merchants, devices, instruments, ips, self.config)
        all_transactions.extend(tx)
        all_ground_truth.extend(gt)
        
        scenarios = [
            SharedDeviceRingScenario(),
            VelocityAbuseScenario(),
            AccountFarmingScenario(),
            RefundAbuseScenario(),
            NetworkExpansionScenario()
        ]
        
        for scenario in scenarios:
            print(f"Generating scenario: {scenario.__class__.__name__}...")
            tx, gt = scenario.generate(customers, merchants, devices, instruments, ips, self.config)
            all_transactions.extend(tx)
            all_ground_truth.extend(gt)
            
        all_transactions.sort(key=lambda x: x['occurred_at'])
        
        if db_url:
            await self.write_to_db(entities, all_transactions, all_ground_truth, db_url)
            
        self.print_summary(entities, all_transactions, all_ground_truth)
        
        return entities, all_transactions, all_ground_truth
    
    async def write_to_db(self, entities, transactions, ground_truth, db_url):
        """Bulk insert generated data into PostgreSQL."""
        from sqlalchemy.ext.asyncio import create_async_engine
        from sqlalchemy import insert
        from app.models.customer import Customer
        from app.models.merchant import Merchant
        from app.models.device import Device
        from app.models.payment_instrument import PaymentInstrument
        from app.models.ip_address import IPAddress
        from app.models.transaction import Transaction
        from app.models.ground_truth import GroundTruth

        print(f"\nConnecting to DB: {db_url.replace(db_url.split('@')[0].split(':')[2], '***')}")
        engine = create_async_engine(db_url)

        try:
            async with engine.begin() as conn:
                if entities.get('customers'):
                    print(f"Inserting {len(entities['customers'])} customers...")
                    await conn.execute(insert(Customer).values(entities['customers']))
                
                if entities.get('merchants'):
                    print(f"Inserting {len(entities['merchants'])} merchants...")
                    await conn.execute(insert(Merchant).values(entities['merchants']))
                
                if entities.get('devices'):
                    print(f"Inserting {len(entities['devices'])} devices...")
                    await conn.execute(insert(Device).values(entities['devices']))
                
                if entities.get('instruments'):
                    print(f"Inserting {len(entities['instruments'])} instruments...")
                    await conn.execute(insert(PaymentInstrument).values(entities['instruments']))
                
                if entities.get('ips'):
                    print(f"Inserting {len(entities['ips'])} IPs...")
                    await conn.execute(insert(IPAddress).values(entities['ips']))
                    
                if transactions:
                    chunk_size = 2000
                    print(f"Inserting {len(transactions)} transactions in chunks of {chunk_size}...")
                    for i in range(0, len(transactions), chunk_size):
                        chunk = transactions[i:i + chunk_size]
                        await conn.execute(insert(Transaction).values(chunk))
                        
                if ground_truth:
                    chunk_size = 2000
                    print(f"Inserting {len(ground_truth)} ground truth labels in chunks of {chunk_size}...")
                    for i in range(0, len(ground_truth), chunk_size):
                        chunk = ground_truth[i:i + chunk_size]
                        await conn.execute(insert(GroundTruth).values(chunk))
                        
            print("Database persistence complete!")
        finally:
            await engine.dispose()
    
    def print_summary(self, entities, transactions, ground_truth):
        """Print dataset statistics: entity counts, abuse ratio, scenario breakdown."""
        print("\n--- Simulation Summary ---")
        print("Entities:")
        for k, v in entities.items():
            print(f"  {k.capitalize()}: {len(v)}")
            
        total_tx = len(transactions)
        abuse_gt = [g for g in ground_truth if g['entity_type'] == 'transaction' and g['is_abuse']]
        abuse_tx_count = len(abuse_gt)
        
        print(f"\nTransactions: {total_tx}")
        print(f"Abuse Transactions: {abuse_tx_count}")
        if total_tx > 0:
            print(f"Abuse Ratio: {abuse_tx_count / total_tx * 100:.2f}%")
            
        print("\nAbuse Types Breakdown (Transactions):")
        types = [g['abuse_type'] for g in abuse_gt]
        counts = Counter(types)
        for t, count in counts.items():
            print(f"  {t}: {count}")

def main():
    parser = argparse.ArgumentParser(
        description="SentinelGraph synthetic fraud and payment transaction data generator."
    )
    parser.add_argument(
        '--db-url',
        type=str,
        default=None,
        help='PostgreSQL database URL (defaults to DATABASE_URL environment variable if set). If omitted, data is generated in memory only without database insertion.'
    )
    parser.add_argument(
        'db_url_pos',
        nargs='?',
        default=None,
        metavar='DB_URL',
        help='Optional positional database URL for backwards compatibility.'
    )
    parser.add_argument(
        '--seed',
        type=int,
        default=None,
        help='Random seed for deterministic generation (defaults to SimulationConfig.seed = 42).'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Generate data in memory only and print summary, without writing to the database.'
    )
    args = parser.parse_args()

    config = SimulationConfig()
    if args.seed is not None:
        config.seed = args.seed

    generator = DataGenerator(config)

    if args.dry_run:
        target_db_url = None
        print("Dry run mode: generating data in memory only, skipping database persistence.")
    else:
        target_db_url = args.db_url or args.db_url_pos or os.getenv('DATABASE_URL')
        if not target_db_url:
            print("Warning: No database URL provided. Data will be generated in memory only.")

    asyncio.run(generator.generate_all(target_db_url))


if __name__ == '__main__':
    main()
