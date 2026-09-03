import uuid
from datetime import datetime, timezone
from typing import List, Dict, Optional, Any
import structlog

logger = structlog.get_logger()


class EvidenceGenerator:
    """Generates structured, template-based evidence records for risk cases.
    
    Evidence descriptions are ALWAYS derived from evidence_data via templates,
    never from free-form text, to guarantee groundedness (§12.2 ADR-003).
    """
    
    SEVERITY_RUBRICS = {
        'device_sharing': [
            (10, 'CRITICAL', 'Extreme device sharing: {count} accounts on single device'),
            (5, 'HIGH', 'High device sharing: {count} accounts on single device'),
            (3, 'MEDIUM', 'Moderate device sharing: {count} accounts on single device'),
        ],
        'ip_sharing': [
            (10, 'CRITICAL', 'Extreme IP sharing: {count} accounts on single IP'),
            (5, 'HIGH', 'High IP sharing: {count} accounts on single IP'),
            (3, 'MEDIUM', 'Moderate IP sharing: {count} accounts on single IP'),
        ],
        'velocity': [
            (5.0, 'CRITICAL', 'Transaction velocity {observed}x above baseline ({baseline} baseline)'),
            (3.0, 'HIGH', 'Transaction velocity {observed}x above baseline ({baseline} baseline)'),
            (2.0, 'MEDIUM', 'Transaction velocity {observed}x above baseline ({baseline} baseline)'),
        ],
        'refund_rate': [
            (0.5, 'CRITICAL', 'Extreme refund rate: {rate:.1%} vs {baseline:.1%} baseline'),
            (0.3, 'HIGH', 'High refund rate: {rate:.1%} vs {baseline:.1%} baseline'),
            (0.15, 'MEDIUM', 'Elevated refund rate: {rate:.1%} vs {baseline:.1%} baseline'),
        ],
        'network_growth': [
            (10, 'CRITICAL', 'Rapid network growth: {count} new connections in {window}'),
            (5, 'HIGH', 'Elevated network growth: {count} new connections in {window}'),
            (3, 'MEDIUM', 'Notable network growth: {count} new connections in {window}'),
        ],
        'shap_feature': [
            (0.15, 'HIGH', 'Top risk factor: {feature_name} (contribution: {contribution:.3f})'),
            (0.05, 'MEDIUM', 'Contributing risk factor: {feature_name} (contribution: {contribution:.3f})'),
        ],
    }

    def generate_deterministic_evidence_id(
        self,
        case_id: uuid.UUID,
        evidence_type: str,
        entity_id: Optional[uuid.UUID],
        dedupe_key: str
    ) -> uuid.UUID:
        """Derive deterministic UUID5 for evidence idempotency across replay."""
        key = f"sentinelgraph:evidence:{str(case_id)}:{evidence_type}:{str(entity_id)}:{dedupe_key}"
        return uuid.uuid5(uuid.NAMESPACE_URL, key)

    def generate_evidence(
        self,
        case_id: uuid.UUID,
        graph_stats: Optional[dict] = None,
        temporal_anomalies: Optional[list] = None,
        shap_features: Optional[list] = None,
        entity_id: Optional[uuid.UUID] = None,
        entity_type: str = 'customer'
    ) -> List[Dict[str, Any]]:
        """Generate template-based evidence records from real signals.
        
        Returns list of dicts matching case_evidence schema:
        - evidence_id: UUID
        - case_id: UUID
        - evidence_type: str
        - entity_type: str
        - entity_id: UUID
        - description: str
        - severity: str (LOW/MEDIUM/HIGH/CRITICAL)
        - evidence_data: dict
        - created_at: datetime
        """
        evidence_records: List[Dict[str, Any]] = []
        now = datetime.now(timezone.utc)
        target_case_id = uuid.UUID(str(case_id)) if not isinstance(case_id, uuid.UUID) else case_id
        target_entity_id = uuid.UUID(str(entity_id)) if entity_id and not isinstance(entity_id, uuid.UUID) else entity_id

        # 1. Temporal Anomalies (Velocity, Refund Rate, Amount)
        if temporal_anomalies:
            for anom in temporal_anomalies:
                anom_type = anom.get('anomaly_type', '')
                obs = float(anom.get('observed_value', 0.0))
                base = float(anom.get('baseline_value', 0.0))
                score = float(anom.get('anomaly_score', 0.0))

                # Velocity spikes
                if 'velocity' in anom_type:
                    ratio = obs / base if base > 0 else obs
                    matched = False
                    for threshold, sev, tmpl in self.SEVERITY_RUBRICS['velocity']:
                        if ratio >= threshold:
                            desc = tmpl.format(observed=round(ratio, 1), baseline=round(base, 2))
                            ev_id = self.generate_deterministic_evidence_id(
                                target_case_id, 'velocity', target_entity_id, f"{anom_type}:{obs}:{base}"
                            )
                            evidence_records.append({
                                'evidence_id': ev_id,
                                'case_id': target_case_id,
                                'evidence_type': 'velocity',
                                'entity_type': entity_type,
                                'entity_id': target_entity_id,
                                'description': desc,
                                'severity': sev,
                                'evidence_data': {
                                    'observed': obs,
                                    'baseline': base,
                                    'ratio': round(ratio, 2),
                                    'anomaly_type': anom_type,
                                    'anomaly_score': score
                                },
                                'created_at': now
                            })
                            matched = True
                            break
                    if not matched and ratio > 1.0:
                        desc = f"Elevated transaction velocity: {obs:.0f} transactions observed vs {base:.2f} baseline"
                        ev_id = self.generate_deterministic_evidence_id(
                            target_case_id, 'velocity', target_entity_id, f"{anom_type}:{obs}:{base}"
                        )
                        evidence_records.append({
                            'evidence_id': ev_id,
                            'case_id': target_case_id,
                            'evidence_type': 'velocity',
                            'entity_type': entity_type,
                            'entity_id': target_entity_id,
                            'description': desc,
                            'severity': 'MEDIUM',
                            'evidence_data': {'observed': obs, 'baseline': base, 'anomaly_type': anom_type},
                            'created_at': now
                        })

                # Refund rate spikes
                elif anom_type == 'refund_spike':
                    for threshold, sev, tmpl in self.SEVERITY_RUBRICS['refund_rate']:
                        if obs >= threshold:
                            desc = tmpl.format(rate=obs, baseline=base)
                            ev_id = self.generate_deterministic_evidence_id(
                                target_case_id, 'refund_rate', target_entity_id, f"refund:{obs}:{base}"
                            )
                            evidence_records.append({
                                'evidence_id': ev_id,
                                'case_id': target_case_id,
                                'evidence_type': 'refund_rate',
                                'entity_type': entity_type,
                                'entity_id': target_entity_id,
                                'description': desc,
                                'severity': sev,
                                'evidence_data': {'rate': obs, 'baseline': base, 'anomaly_score': score},
                                'created_at': now
                            })
                            break

                # Amount anomaly
                elif anom_type == 'amount_anomaly':
                    sev = 'CRITICAL' if score >= 5.0 else ('HIGH' if score >= 3.0 else 'MEDIUM')
                    desc = f"Unusual transaction amount pattern: ${obs:.2f} vs historical mean ${base:.2f} (z-score: {score:.1f})"
                    ev_id = self.generate_deterministic_evidence_id(
                        target_case_id, 'amount_anomaly', target_entity_id, f"amount:{obs}:{base}"
                    )
                    evidence_records.append({
                        'evidence_id': ev_id,
                        'case_id': target_case_id,
                        'evidence_type': 'amount_anomaly',
                        'entity_type': entity_type,
                        'entity_id': target_entity_id,
                        'description': desc,
                        'severity': sev,
                        'evidence_data': {'observed': obs, 'baseline': base, 'anomaly_score': score},
                        'created_at': now
                    })

        # 2. Graph Statistics (Device/IP sharing, Network Growth)
        if graph_stats:
            # Device sharing
            dev_count = int(graph_stats.get('device_account_count', 0))
            if dev_count >= 3:
                for threshold, sev, tmpl in self.SEVERITY_RUBRICS['device_sharing']:
                    if dev_count >= threshold:
                        desc = tmpl.format(count=dev_count)
                        ev_id = self.generate_deterministic_evidence_id(
                            target_case_id, 'device_sharing', target_entity_id, f"device:{dev_count}"
                        )
                        evidence_records.append({
                            'evidence_id': ev_id,
                            'case_id': target_case_id,
                            'evidence_type': 'device_sharing',
                            'entity_type': entity_type,
                            'entity_id': target_entity_id,
                            'description': desc,
                            'severity': sev,
                            'evidence_data': {'count': dev_count},
                            'created_at': now
                        })
                        break

            # IP sharing
            ip_count = int(graph_stats.get('ip_account_count', 0))
            if ip_count >= 3:
                for threshold, sev, tmpl in self.SEVERITY_RUBRICS['ip_sharing']:
                    if ip_count >= threshold:
                        desc = tmpl.format(count=ip_count)
                        ev_id = self.generate_deterministic_evidence_id(
                            target_case_id, 'ip_sharing', target_entity_id, f"ip:{ip_count}"
                        )
                        evidence_records.append({
                            'evidence_id': ev_id,
                            'case_id': target_case_id,
                            'evidence_type': 'ip_sharing',
                            'entity_type': entity_type,
                            'entity_id': target_entity_id,
                            'description': desc,
                            'severity': sev,
                            'evidence_data': {'count': ip_count},
                            'created_at': now
                        })
                        break

            # Network growth
            growth_count = int(graph_stats.get('network_growth', 0))
            window_str = str(graph_stats.get('window', '24h'))
            if growth_count >= 3:
                for threshold, sev, tmpl in self.SEVERITY_RUBRICS['network_growth']:
                    if growth_count >= threshold:
                        desc = tmpl.format(count=growth_count, window=window_str)
                        ev_id = self.generate_deterministic_evidence_id(
                            target_case_id, 'network_growth', target_entity_id, f"growth:{growth_count}:{window_str}"
                        )
                        evidence_records.append({
                            'evidence_id': ev_id,
                            'case_id': target_case_id,
                            'evidence_type': 'network_growth',
                            'entity_type': entity_type,
                            'entity_id': target_entity_id,
                            'description': desc,
                            'severity': sev,
                            'evidence_data': {'count': growth_count, 'window': window_str},
                            'created_at': now
                        })
                        break

        # 3. Model SHAP Feature Contributions
        if shap_features:
            for feat in shap_features:
                contrib = float(feat.get('contribution', 0.0))
                fname = str(feat.get('name') or feat.get('feature_name', ''))
                fval = feat.get('value')
                if contrib >= 0.05 and fname:
                    for threshold, sev, tmpl in self.SEVERITY_RUBRICS['shap_feature']:
                        if contrib >= threshold:
                            desc = tmpl.format(feature_name=fname, contribution=contrib)
                            ev_id = self.generate_deterministic_evidence_id(
                                target_case_id, 'shap_feature', target_entity_id, f"shap:{fname}"
                            )
                            evidence_records.append({
                                'evidence_id': ev_id,
                                'case_id': target_case_id,
                                'evidence_type': 'shap_feature',
                                'entity_type': entity_type,
                                'entity_id': target_entity_id,
                                'description': desc,
                                'severity': sev,
                                'evidence_data': {
                                    'feature_name': fname,
                                    'contribution': round(contrib, 4),
                                    'value': fval
                                },
                                'created_at': now
                            })
                            break

        return evidence_records
