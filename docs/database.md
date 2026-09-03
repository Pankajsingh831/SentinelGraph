# SentinelGraph — Database Documentation

## PostgreSQL Schema (18 Tables)

### Entity Tables
| Table | PK | Description |
|-------|-----|-------------|
| `customers` | `customer_id` (UUID) | Payment platform customers |
| `merchants` | `merchant_id` (UUID) | Merchants accepting payments |
| `devices` | `device_id` (UUID) | Devices used for transactions |
| `payment_instruments` | `instrument_id` (UUID) | Cards, wallets, bank accounts |
| `ip_addresses` | `ip_id` (UUID) | Hashed IP addresses |

### Transaction Tables
| Table | PK | Description |
|-------|-----|-------------|
| `transactions` | `transaction_id` (UUID) | All payment transactions |
| `entity_relationships` | `relationship_id` (UUID) | Postgres mirror of Neo4j graph edges |

### ML Tables
| Table | PK | Description |
|-------|-----|-------------|
| `risk_features` | `feature_id` (UUID) | Computed feature vectors |
| `risk_predictions` | `prediction_id` (UUID) | XGBoost predictions per transaction |
| `model_versions` | `id` (BIGSERIAL) | Trained model registry |
| `ground_truth` | `id` (BIGSERIAL) | Simulator abuse labels |

### Risk & Intelligence Tables
| Table | PK | Description |
|-------|-----|-------------|
| `temporal_anomalies` | `anomaly_id` (UUID) | Detected temporal anomalies |
| `network_risks` | `network_id` (UUID) | Network/community risk scores |

### Case Management Tables
| Table | PK | Description |
|-------|-----|-------------|
| `risk_cases` | `case_id` (UUID) | Auto-generated risk investigation cases |
| `case_entities` | `id` (BIGSERIAL) | Entities linked to a case |
| `case_evidence` | `evidence_id` (UUID) | Template-grounded evidence records |
| `analyst_decisions` | `decision_id` (UUID) | Analyst verdicts per case |
| `audit_logs` | `audit_id` (UUID) | Full audit trail |

### Auth Tables
| Table | PK | Description |
|-------|-----|-------------|
| `users` | `user_id` (UUID) | Platform users (ANALYST/ADMIN roles) |

## Neo4j Graph Model

### Node Labels
- `:Customer` — `{id, updated_at}`
- `:Merchant` — `{id, updated_at}`
- `:Device` — `{id, updated_at}`
- `:PaymentInstrument` — `{id, updated_at}`
- `:IPAddress` — `{id, updated_at}`
- `:Transaction` — `{id, amount, occurred_at}`

### Relationship Types
- `(Customer)-[:MADE]->(Transaction)`
- `(Transaction)-[:PAID_TO]->(Merchant)`
- `(Transaction)-[:USED_DEVICE]->(Device)`
- `(Transaction)-[:USED_INSTRUMENT]->(PaymentInstrument)`
- `(Transaction)-[:FROM_IP]->(IPAddress)`
- `(Customer)-[:USES]->(Device|PaymentInstrument|IPAddress)`

### Constraints
Uniqueness constraints on all node `id` properties. See `graph/constraints.cypher`.

## Fallback Architecture

When Neo4j is unavailable, the system falls back to querying `entity_relationships` in PostgreSQL. API responses include `degraded: true` to indicate partial signal.
