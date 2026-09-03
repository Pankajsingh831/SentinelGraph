# SentinelGraph — 5-Minute Demo Script

## Prerequisites

- Docker Desktop running
- `.env` file configured (copy from `.env.example`)
- At least 8GB RAM available for Docker

## Demo Flow

### Step 1: Start the Platform (30 seconds)

```bash
cp .env.example .env
make up
# Wait for health checks to pass
make health
```

Expected output: `{"status": "healthy", "services": {"postgres": true, "redis": true, "neo4j": true}}`

### Step 2: Run Database Migrations (10 seconds)

```bash
make migrate
```

### Step 3: Generate Synthetic Data (60 seconds)

```bash
make simulate
```

**Narration**: "The simulator generates 50,000 normal transactions and injects 5 types of coordinated abuse: shared device rings, velocity abuse, account farming, refund abuse, and network expansion. Each abuse pattern is individually subtle — the key question is whether our models can detect them."

### Step 4: Train Models (90 seconds)

```bash
make train
```

**Narration**: "We train three models: a logistic regression baseline, XGBoost on transaction/temporal/behavioral features only, and XGBoost with graph features added. The central experiment is whether graph features improve detection of coordinated abuse."

### Step 5: Show Evaluation Results (30 seconds)

```bash
make evaluate
```

**Narration**: "Model 2 (XGBoost + Graph) achieves ~91% PR-AUC compared to ~82% for Model 1 without graph features. The largest improvements are in detecting shared device rings (+67%) and account farming (+120%) — patterns that are invisible to non-graph models."

### Step 6: Open the Dashboard (30 seconds)

Open http://localhost:3000 in a browser.

Login with: `analyst` / `analyst123`

**Narration**: "The analyst dashboard shows all auto-generated risk cases, sorted by severity. Each case was automatically created when the risk aggregator detected a high enough combined score."

### Step 7: Investigate a Case (60 seconds)

1. Click a CRITICAL-tier case from the dashboard
2. **Risk Scores Panel**: Show the overall score gauge and the breakdown (transaction / network / temporal)
3. **Evidence Tab**: Walk through the template-generated evidence — each is grounded in structured data
4. **Graph Tab**: Show the interactive network graph — highlight the shared device connections
5. **Timeline Tab**: Show the chronological reconstruction

### Step 8: AI Investigation (30 seconds)

1. Click "Investigate with AI"
2. **Narration**: "The AI Investigator uses Claude with tool-calling to analyze the case. It receives the evidence, SHAP features, graph statistics, and timeline as context. Its output is schema-validated and grounded — every cited evidence ID is cross-checked against real database records."
3. Show the generated report: summary, key evidence (linked), recommended action, confidence

### Step 9: Make a Decision (15 seconds)

1. Select "CONFIRMED_ABUSE" from the decision buttons
2. Enter reason: "Multiple accounts sharing same device and IP, coordinated transaction timing consistent with abuse ring."
3. Submit — case moves to RESOLVED, audit log entry created

### Step 10: Detection Replay (30 seconds)

1. Navigate to Detection Replay
2. Select "shared_device_ring" scenario
3. Play the replay — watch transactions stream in, the graph build, and the risk score climb
4. **Narration**: "Detection Replay lets analysts understand *how* an abuse pattern was detected over time. This is the forensic investigation mode."

### Step 11: Architecture Summary (30 seconds)

**Narration**: "SentinelGraph combines real-time XGBoost scoring, asynchronous graph intelligence via Neo4j, temporal anomaly detection, evidence-grounded AI investigation, and an analyst decision workflow — all in a single platform. The key insight is that graph features provide the largest uplift for detecting coordinated abuse that individual transaction models miss."

## Key Demo Points

1. **Graph features matter**: Model 2 vs Model 1 shows significant improvement
2. **Evidence is grounded**: Every piece of evidence traces to structured data
3. **AI is constrained**: The investigator can only cite real evidence IDs
4. **System degrades gracefully**: Kill Neo4j and show the fallback mode
5. **Full audit trail**: Every decision is logged with actor, action, and timestamp
