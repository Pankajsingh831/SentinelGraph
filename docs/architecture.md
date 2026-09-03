# SentinelGraph — Architecture

## System Overview

SentinelGraph is an AI-assisted payment-abuse detection platform that combines real-time ML scoring with graph-based network intelligence and temporal anomaly detection.

## Architecture Diagram

```
┌──────────────┐     ┌──────────────────┐     ┌──────────────────┐
│   Next.js    │────▶│   FastAPI API     │────▶│   PostgreSQL     │
│   Dashboard  │     │   (Port 8000)     │     │   (Port 5432)    │
│  (Port 3000) │     │                   │     │   18 tables      │
└──────────────┘     │ • Risk Scoring    │     └──────────────────┘
                     │ • Case Management │
                     │ • AI Investigator │     ┌──────────────────┐
                     │ • Graph APIs      │────▶│   Neo4j          │
                     │ • Auth (JWT)      │     │   (Port 7687)    │
                     └────────┬──────────┘     │   Graph model    │
                              │                └──────────────────┘
                              │ Kafka Events
                              ▼                ┌──────────────────┐
                     ┌──────────────────┐      │   Redis          │
                     │   Apache Kafka   │      │   (Port 6379)    │
                     │   (KRaft mode)   │      │   Feature cache  │
                     │   3 topics       │      └──────────────────┘
                     └────────┬─────────┘
                              │
              ┌───────────────┼───────────────┐
              ▼               ▼               ▼
     ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
     │ Graph Worker  │ │  Temporal    │ │ Case Worker   │
     │              │ │  Worker      │ │              │
     │ Neo4j MERGE  │ │ Anomaly Det. │ │ Risk Aggreg. │
     │ Postgres sync│ │ Z-score      │ │ Evidence Gen.│
     └──────────────┘ └──────────────┘ └──────────────┘
```

## Data Flow

1. **Transaction Ingestion**: Simulator generates transactions → written to PostgreSQL
2. **Real-Time Scoring**: `POST /risk/score` → feature extraction → XGBoost inference → risk tier classification → persist prediction
3. **Event Publishing**: Scored transaction published to Kafka `payment.events`
4. **Graph Processing**: Graph Worker consumes event → MERGEs nodes/relationships in Neo4j → syncs to Postgres `entity_relationships` → publishes `graph.updates`
5. **Temporal Processing**: Temporal Worker computes velocity/anomaly scores → persists `temporal_anomalies` → publishes `temporal.updates`
6. **Case Creation**: Case Worker aggregates signals → creates `risk_cases` when threshold exceeded → generates evidence
7. **Investigation**: Analyst views case → triggers AI Investigator → grounded report generated → analyst makes decision

## Key Design Decisions (ADRs)

### ADR-001: Neo4j with Postgres Fallback
- **Decision**: Neo4j as primary graph DB, Postgres `entity_relationships` table as fallback
- **Rationale**: Neo4j excels at graph queries but adds operational complexity. Fallback ensures the system degrades gracefully, returning `degraded: true` in API responses

### ADR-002: KRaft-mode Kafka (No Zookeeper)
- **Decision**: Apache Kafka 3.7 in KRaft mode
- **Rationale**: Simpler deployment (single container), production-ready since Kafka 3.3, eliminates ZooKeeper synchronization issues

### ADR-003: Evidence Grounding
- **Decision**: All evidence descriptions are template-derived from structured `evidence_data` (JSONB)
- **Rationale**: Ensures every claim is traceable to data. AI Investigator's `key_evidence` IDs are cross-checked against real `case_evidence` rows

### ADR-004: Chronological ML Split
- **Decision**: 70/15/15 chronological split (oldest → newest), never random
- **Rationale**: Prevents temporal leakage. Models are evaluated on future data they haven't seen during training

### ADR-005: SHAP for Explainability
- **Decision**: SHAP TreeExplainer for per-prediction feature contributions
- **Rationale**: Model-agnostic, mathematically grounded, fast for tree models. Top-5 features shown to analyst per case

## Component Details

### Frontend (Next.js 14)
- App Router with TypeScript strict mode
- React Query for server state management
- React Flow for interactive graph visualization
- Radix UI for accessible component primitives
- Tailwind CSS dark theme

### Backend (FastAPI)
- Async SQLAlchemy 2.0 with asyncpg driver
- Pydantic v2 for request/response validation
- JWT authentication with RBAC (ANALYST/ADMIN)
- Structured JSON logging via structlog
- Prometheus metrics export

### ML Pipeline
- XGBoost classifier with SHAP explainability
- 4 feature groups: transaction, temporal, behavioral, graph
- 3-model comparison: LogReg baseline → XGBoost → XGBoost+Graph
- Leakage-guarded feature pipeline

### Workers (Kafka Consumers)
- Graph Worker: Neo4j MERGE + Postgres entity_relationships sync
- Temporal Worker: Z-score anomaly detection against rolling baselines
- Case Worker: Risk aggregation + evidence generation
