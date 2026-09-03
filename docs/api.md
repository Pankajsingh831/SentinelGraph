# SentinelGraph — API Reference

## Base URL

```
http://localhost:8000/api/v1
```

## Authentication

All endpoints (except `/health` and `/auth/login`) require a Bearer token:

```
Authorization: Bearer <jwt_token>
```

Obtain a token via `POST /auth/login`.

## Endpoints

### Health

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Service health check |

### Auth

| Method | Path | Description |
|--------|------|-------------|
| POST | `/auth/login` | Authenticate and get JWT token |

**Request**: `{ "username": "analyst", "password": "analyst123" }`
**Response**: `{ "token": "eyJ...", "user": { "user_id": "...", "username": "analyst", "role": "ANALYST" } }`

### Risk Scoring

| Method | Path | Description |
|--------|------|-------------|
| POST | `/risk/score` | Score a transaction (FR-001) |
| GET | `/risk/predictions/{prediction_id}/explanation` | SHAP feature breakdown (F-08) |

### Cases

| Method | Path | Description |
|--------|------|-------------|
| GET | `/cases` | List cases with filters (FR-008) |
| GET | `/cases/{case_id}` | Get case detail |
| GET | `/cases/{case_id}/evidence` | Get case evidence (FR-003) |
| GET | `/cases/{case_id}/timeline` | Get case timeline (FR-009) |
| POST | `/cases/{case_id}/investigate` | AI investigation (FR-004) |
| POST | `/cases/{case_id}/decision` | Record analyst decision (FR-005) |

### Graph

| Method | Path | Description |
|--------|------|-------------|
| GET | `/graph/entity/{entity_type}/{entity_id}` | Entity graph |
| GET | `/graph/entity/{entity_type}/{entity_id}/neighbors` | Bounded neighbors (depth≤3, limit≤200) |

### Networks

| Method | Path | Description |
|--------|------|-------------|
| GET | `/networks/{network_id}` | Network stats |
| GET | `/networks/{network_id}/graph` | Network graph visualization |

### Transactions & Customers

| Method | Path | Description |
|--------|------|-------------|
| GET | `/transactions/{transaction_id}` | Get transaction |
| GET | `/customers/{customer_id}` | Get customer |

## Error Handling

All errors return:
```json
{
  "error": {
    "code": "RESOURCE_NOT_FOUND",
    "message": "Transaction not found",
    "request_id": "abc-123"
  }
}
```

Standard error codes: `VALIDATION_ERROR` (422), `UNAUTHORIZED` (401), `FORBIDDEN` (403), `RESOURCE_NOT_FOUND` (404), `CONFLICT` (409), `INTERNAL_ERROR` (500).
