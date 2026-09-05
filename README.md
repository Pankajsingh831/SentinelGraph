# SentinelGraph

Demonstation/video
## 🎥 Project Demo

[▶️ Watch Project Demo](https://drive.google.com/file/d/1OuK_Ddy6FADIWiO0kerjzHGxrWcApOOs/view?usp=drivesdk)


**AI-Assisted Payment Abuse Detection & Investigation Platform**

> Transaction-level fraud models miss *coordinated* abuse — individually normal-looking transactions that become suspicious only when viewed as a network. SentinelGraph combines real-time ML scoring, graph intelligence, temporal anomaly detection, and evidence-grounded AI investigation in a single analyst workbench.

## Architecture

```
Next.js Dashboard ─▶ FastAPI API ─▶ PostgreSQL (18 tables)
     (3000)           (8000)    ├──▶ Neo4j (graph model)
                        │       └──▶ Redis (feature cache)
                        │
                   Apache Kafka (KRaft)
                        │
            ┌───────────┼───────────┐
        Graph Worker  Temporal    Case Worker
        (Neo4j sync)  Worker     (risk aggregation
                     (anomaly     + evidence gen)
                      detection)
```

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Next.js 14, TypeScript, Tailwind CSS, React Flow, Radix UI, React Query |
| API | FastAPI, Pydantic v2, SQLAlchemy 2.0 (async), JWT Auth |
| ML | XGBoost, SHAP, scikit-learn, NumPy, Pandas |
| AI | Claude (Anthropic API) with tool-calling, evidence grounding |
| Graph | Neo4j 5.x (Cypher), Postgres fallback |
| Messaging | Apache Kafka 3.7 (KRaft mode) |
| Database | PostgreSQL 16, Redis 7.x |
| Infrastructure | Docker Compose, GitHub Actions CI |

## Quick Start

### Prerequisites
- Docker Desktop (8GB+ RAM)
- Git

### Setup
```bash
git clone <repo-url> sentinelgraph
cd sentinelgraph
cp .env.example .env
make up          # Start all services
make migrate     # Run database migrations
make simulate    # Generate synthetic data (50K+ transactions)
make train       # Train ML models (LogReg, XGBoost, XGBoost+Graph)
make evaluate    # Generate evaluation report
```

### Access
- **Dashboard**: http://localhost:3000 (login: `analyst` / `analyst123`)
- **API**: http://localhost:8000/docs (Swagger UI)
- **Neo4j Browser**: http://localhost:7474 (neo4j / sentinel_password)

## Project Structure

```
sentinelgraph/
├── apps/
│   ├── api/                    # FastAPI backend
│   │   ├── app/
│   │   │   ├── api/            # Route handlers
│   │   │   ├── events/         # Kafka producer & event schemas
│   │   │   ├── graph/          # Neo4j client & Cypher queries
│   │   │   ├── middleware/     # Auth, logging, request-ID
│   │   │   ├── models/         # SQLAlchemy ORM models (18)
│   │   │   ├── repositories/   # Database access layer
│   │   │   ├── schemas/        # Pydantic request/response models
│   │   │   └── services/       # Business logic + AI investigator
│   │   └── alembic/            # Database migrations
│   └── web/                    # Next.js frontend
│       ├── app/                # Pages (App Router)
│       ├── components/         # React components
│       │   ├── ai-investigator/
│       │   ├── evidence/
│       │   ├── graph/          # React Flow visualization
│       │   ├── layout/
│       │   ├── risk-score/
│       │   ├── timeline/
│       │   └── ui/             # Shared UI primitives
│       └── lib/                # API client, hooks, types, auth
├── services/
│   ├── graph-worker/           # Kafka → Neo4j + Postgres sync
│   ├── temporal-worker/        # Temporal anomaly detection
│   └── case-worker/            # Risk aggregation + evidence generation
├── simulator/                  # Synthetic data generator
│   └── scenarios/              # 5 abuse patterns + normal traffic
├── ml/                         # ML pipeline
│   ├── features/               # Feature engineering (4 groups)
│   └── training/               # Train, evaluate, explain (SHAP)
├── graph/                      # Neo4j constraints & init
├── docs/                       # Documentation
├── docker-compose.yml          # Full infrastructure
├── Makefile                    # Developer workflow
└── .github/workflows/ci.yml   # CI pipeline
```

## ML Experiment

The central experiment compares three models on synthetic abuse detection:

| Model | Description | PR-AUC |
|-------|------------|--------|
| Model 0 | Logistic Regression (baseline) | ~0.65 |
| Model 1 | XGBoost (transaction + temporal + behavioral) | ~0.82 |
| **Model 2** | **XGBoost + graph features** | **~0.91** |

Graph features (`device_account_count`, `network_size`, etc.) provide **+11% PR-AUC uplift**, with the largest gains in detecting shared device rings (+67%) and account farming (+120%).

See [docs/evaluation_results.md](docs/evaluation_results.md) for full results.

## Development

```bash
make help        # List all available commands
make test        # Run all tests
make lint        # Run linters (ruff + eslint)
make logs        # Follow Docker logs
make clean       # Stop services and remove volumes
```

## Documentation

- [Architecture](docs/architecture.md) — System design, data flow, ADRs
- [API Reference](docs/api.md) — Endpoint documentation
- [Database](docs/database.md) — Schema, ER diagram, Neo4j model
- [ML Pipeline](docs/ml.md) — Features, models, evaluation methodology
- [Security](docs/security.md) — Auth, RBAC, threat model
- [Demo Script](docs/demo.md) — 5-minute presentation walkthrough
- [Evaluation Results](docs/evaluation_results.md) — Model comparison

## License

MIT
