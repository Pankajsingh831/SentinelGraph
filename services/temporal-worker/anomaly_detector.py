import uuid
import numpy as np
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Optional
import structlog

logger = structlog.get_logger()

class TemporalAnomalyDetector:
    """Detects temporal anomalies by comparing current behavior against rolling baselines."""
    
    ANOMALY_TYPES = [
        'velocity_spike_5m',       # transactions in 5min vs baseline
        'velocity_spike_1h',       # transactions in 1h vs baseline  
        'velocity_spike_24h',      # transactions in 24h vs baseline
        'account_creation_spike',  # new accounts from same device/IP in window
        'refund_spike',            # refund rate vs baseline
        'amount_anomaly',          # unusual amount pattern
    ]
    
    def __init__(self, z_score_threshold: float = 2.5):
        self.z_score_threshold = float(z_score_threshold)
    
    def _compute_z_score(self, observed: float, mean: float, std: float) -> float:
        """Compute standard Z-score with zero standard deviation guard."""
        if std == 0 or np.isnan(std):
            return 0.0 if observed == mean else 3.0
        score = abs(observed - mean) / std
        if np.isnan(score) or np.isinf(score):
            return 0.0
        return float(score)
    
    def compute_baseline_stats(self, historical_counts: list) -> dict:
        """Compute mean and std from historical observation windows."""
        if not historical_counts:
            return {'mean': 0.0, 'std': 1.0}
        clean_counts = [float(x) for x in historical_counts if not (np.isnan(x) or np.isinf(x))]
        if not clean_counts:
            return {'mean': 0.0, 'std': 1.0}
        mean_val = float(np.mean(clean_counts))
        std_val = float(max(np.std(clean_counts), 0.1))
        return {'mean': mean_val, 'std': std_val}

    def generate_deterministic_anomaly_id(
        self,
        entity_type: str,
        entity_id: str,
        anomaly_type: str,
        window_end: datetime
    ) -> uuid.UUID:
        """Derive deterministic UUID for anomaly to ensure application-level idempotency."""
        iso_time = window_end.isoformat()
        key = f"sentinelgraph:temporal:{entity_type}:{entity_id}:{anomaly_type}:{iso_time}"
        return uuid.uuid5(uuid.NAMESPACE_URL, key)

    def detect_anomalies(
        self,
        entity_id: str,
        entity_type: str,
        current_stats: dict,
        baseline_stats: dict,
        window_start: datetime,
        window_end: datetime
    ) -> List[Dict]:
        """Compare current stats against baseline, return anomalies.
        
        current_stats: {tx_count_5m, tx_count_1h, tx_count_24h, refund_rate, avg_amount, amount}
        baseline_stats: {mean_tx_5m, std_tx_5m, mean_tx_1h, std_tx_1h, mean_tx_24h, std_tx_24h,
                         mean_refund_rate, std_refund_rate, mean_amount, std_amount, amount_sample_count}
        
        Returns list of anomaly dicts matching temporal_anomalies schema:
        [{anomaly_id, entity_type, entity_id, anomaly_type, baseline_value, 
          observed_value, anomaly_score, window_start, window_end, detected_at}]
        """
        anomalies = []
        now = datetime.now(timezone.utc)
        
        # 1. Velocity spike 5m
        obs_5m = float(current_stats.get('tx_count_5m', 0))
        mean_5m = float(baseline_stats.get('mean_tx_5m', 0.1))
        std_5m = float(baseline_stats.get('std_tx_5m', 0.5))
        z_5m = self._compute_z_score(obs_5m, mean_5m, std_5m)
        if z_5m >= self.z_score_threshold and obs_5m > mean_5m:
            w_start = window_end - timedelta(minutes=5)
            anom_id = self.generate_deterministic_anomaly_id(entity_type, entity_id, 'velocity_spike_5m', window_end)
            anomalies.append({
                'anomaly_id': anom_id,
                'entity_type': entity_type,
                'entity_id': uuid.UUID(str(entity_id)) if not isinstance(entity_id, uuid.UUID) else entity_id,
                'anomaly_type': 'velocity_spike_5m',
                'baseline_value': mean_5m,
                'observed_value': obs_5m,
                'anomaly_score': round(z_5m, 4),
                'window_start': w_start,
                'window_end': window_end,
                'detected_at': now
            })
            
        # 2. Velocity spike 1h
        obs_1h = float(current_stats.get('tx_count_1h', 0))
        mean_1h = float(baseline_stats.get('mean_tx_1h', 0.5))
        std_1h = float(baseline_stats.get('std_tx_1h', 1.0))
        z_1h = self._compute_z_score(obs_1h, mean_1h, std_1h)
        if z_1h >= self.z_score_threshold and obs_1h > mean_1h:
            w_start = window_end - timedelta(hours=1)
            anom_id = self.generate_deterministic_anomaly_id(entity_type, entity_id, 'velocity_spike_1h', window_end)
            anomalies.append({
                'anomaly_id': anom_id,
                'entity_type': entity_type,
                'entity_id': uuid.UUID(str(entity_id)) if not isinstance(entity_id, uuid.UUID) else entity_id,
                'anomaly_type': 'velocity_spike_1h',
                'baseline_value': mean_1h,
                'observed_value': obs_1h,
                'anomaly_score': round(z_1h, 4),
                'window_start': w_start,
                'window_end': window_end,
                'detected_at': now
            })

        # 3. Velocity spike 24h
        obs_24h = float(current_stats.get('tx_count_24h', 0))
        mean_24h = float(baseline_stats.get('mean_tx_24h', 1.0))
        std_24h = float(baseline_stats.get('std_tx_24h', 1.0))
        z_24h = self._compute_z_score(obs_24h, mean_24h, std_24h)
        if z_24h >= self.z_score_threshold and obs_24h > mean_24h:
            w_start = window_end - timedelta(hours=24)
            anom_id = self.generate_deterministic_anomaly_id(entity_type, entity_id, 'velocity_spike_24h', window_end)
            anomalies.append({
                'anomaly_id': anom_id,
                'entity_type': entity_type,
                'entity_id': uuid.UUID(str(entity_id)) if not isinstance(entity_id, uuid.UUID) else entity_id,
                'anomaly_type': 'velocity_spike_24h',
                'baseline_value': mean_24h,
                'observed_value': obs_24h,
                'anomaly_score': round(z_24h, 4),
                'window_start': w_start,
                'window_end': window_end,
                'detected_at': now
            })

        # 4. Refund spike
        obs_refund = float(current_stats.get('refund_rate', 0.0))
        mean_refund = float(baseline_stats.get('mean_refund_rate', 0.0))
        std_refund = float(baseline_stats.get('std_refund_rate', 0.1))
        # Requires at least 2 transactions in 24h and positive refund observation
        if obs_24h >= 2 and obs_refund > mean_refund:
            z_refund = self._compute_z_score(obs_refund, mean_refund, std_refund)
            if z_refund >= self.z_score_threshold:
                w_start = window_end - timedelta(hours=24)
                anom_id = self.generate_deterministic_anomaly_id(entity_type, entity_id, 'refund_spike', window_end)
                anomalies.append({
                    'anomaly_id': anom_id,
                    'entity_type': entity_type,
                    'entity_id': uuid.UUID(str(entity_id)) if not isinstance(entity_id, uuid.UUID) else entity_id,
                    'anomaly_type': 'refund_spike',
                    'baseline_value': mean_refund,
                    'observed_value': obs_refund,
                    'anomaly_score': round(z_refund, 4),
                    'window_start': w_start,
                    'window_end': window_end,
                    'detected_at': now
                })

        # 5. Amount anomaly
        amount_sample_count = int(baseline_stats.get('amount_sample_count', 0))
        if amount_sample_count >= 3:
            obs_amt = float(current_stats.get('amount', current_stats.get('avg_amount', 0.0)))
            mean_amt = float(baseline_stats.get('mean_amount', 0.0))
            std_amt = float(baseline_stats.get('std_amount', 1.0))
            z_amt = self._compute_z_score(obs_amt, mean_amt, std_amt)
            if z_amt >= self.z_score_threshold and obs_amt > mean_amt:
                w_start = window_end - timedelta(minutes=5)
                anom_id = self.generate_deterministic_anomaly_id(entity_type, entity_id, 'amount_anomaly', window_end)
                anomalies.append({
                    'anomaly_id': anom_id,
                    'entity_type': entity_type,
                    'entity_id': uuid.UUID(str(entity_id)) if not isinstance(entity_id, uuid.UUID) else entity_id,
                    'anomaly_type': 'amount_anomaly',
                    'baseline_value': mean_amt,
                    'observed_value': obs_amt,
                    'anomaly_score': round(z_amt, 4),
                    'window_start': w_start,
                    'window_end': window_end,
                    'detected_at': now
                })

        return anomalies
