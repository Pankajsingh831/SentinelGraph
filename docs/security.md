# SentinelGraph — Security

## Authentication

- **Mechanism**: JWT (JSON Web Tokens) with HS256 signing
- **Token Lifetime**: 8 hours (480 minutes, configurable via `JWT_EXPIRATION_MINUTES`)
- **Password Hashing**: bcrypt via `passlib`
- **Development Mode**: When `JWT_SECRET=development`, auth is bypassed with a mock analyst user

## Role-Based Access Control (RBAC)

| Role | Permissions |
|------|------------|
| `ANALYST` | View cases, view evidence, investigate with AI, record decisions, view graphs |
| `ADMIN` | All analyst permissions + user management |

## API Security

- **CORS**: Restricted to `http://localhost:3000` (configurable)
- **Request IDs**: Every request gets a unique `X-Request-ID` for tracing
- **Input Validation**: Pydantic v2 validates all request bodies
- **SQL Injection**: Prevented by SQLAlchemy parameterized queries
- **Cypher Injection**: Prevented by parameterized Neo4j queries

## Data Protection

- **IP Addresses**: Never stored in plaintext — only SHA256 hashes (`ip_hash`)
- **Secrets**: All secrets via environment variables, never hardcoded
- **Audit Logging**: All analyst actions logged to `audit_logs` with actor, action, resource, timestamp
- **AI Grounding**: AI Investigator output is schema-validated and evidence-grounded — cannot hallucinate evidence IDs

## Threat Model

| Threat | Mitigation |
|--------|-----------|
| JWT token theft | Short-lived tokens (8h), secure storage guidance |
| SQL/Cypher injection | Parameterized queries throughout |
| AI hallucination | Evidence grounding validator cross-checks all cited IDs |
| Unauthorized access | JWT auth + RBAC on all endpoints |
| Data exfiltration | IP hashing, no PII in logs |
| Service compromise | Kafka workers are read-only consumers, Neo4j fallback |

## Environment Variables

All secrets are configured via `.env` file:
- `JWT_SECRET` — must be changed from default in production
- `ANTHROPIC_API_KEY` — AI provider key
- `NEO4J_PASSWORD` — graph database password
- Database passwords — Postgres, Redis
