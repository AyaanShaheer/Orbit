# 🎬 ORBIT — Judge Demo Guide

> A step-by-step walkthrough for evaluating ORBIT's 4 Demonstration Scenes + Comparative Benchmark.

---

## ⚡ 2-Minute Setup

```powershell
# 1. Start FalkorDB (official image — no setup needed)
docker compose up -d

# 2. Install dependencies (first time only)
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

# 3. Verify: all 14 automated tests pass (takes ~3 seconds)
python -m pytest -v

# 4. Launch Mission Control UI
.\scripts\start_ui.ps1
```

Open **http://localhost:8501** in your browser.

---

## 🔑 The Central Claim Judges Should Verify

> **"FalkorDB is not decoration here. Remove it, and the entire system collapses — no memory recall, no contradiction detection, no concurrency locking, no auditable replay."**

Every decision made by the 4 agents is backed by live Cypher queries returning graph entities from FalkorDB. You can verify this in real-time via the Graph Explorer tab.

---

## 🎬 Scene-by-Scene Demo Script

### **Scene 1: The Cold Start** (~20 seconds)

**Purpose:** Prove agents use FalkorDB — not chat history — for memory.

1. Open Tab 1 (Incident Simulator)
2. Select **"Scene 1: The Cold Start"**
3. Click **🚀 Run Scene**

**What to look for:**
- The blue callout: **"Zero prior chat tokens or in-memory messages"**
- `falkordb_memories_retrieved` count is **> 0** — memories come from the graph
- The Cypher query in the timeline step shows: `MATCH (i:Incident {service: 'checkout-service'})-[:HAS_EPISODE]->(e)-[:CONTAINS]->(o)-[:SUPPORTS]->(f)...`
- `execution_time_ms` is under 30ms — real multi-hop FalkorDB query performance

**Disqualification check:** This would fail completely if FalkorDB were replaced with a vector store or flat file — there is no "chat history" to fall back on.

---

### **Scene 2: Agents Disagree & Reconcile** (~40 seconds)

**Purpose:** Show multi-agent contradiction detection backed by live graph evidence.

1. Select **"Scene 2: Agents Disagree & Reconcile"**
2. Click **🚀 Run Scene**

**What to look for:**
- The red conflict banner shows **2 contradictions detected**
- Each contradiction includes:
  - `prior_fact_content`: the stale historical belief from `INC-2026-0901`
  - `new_claim`: what the Systems Agent found via topology traversal in FalkorDB
  - `resolution`: `differentiated_by_version` or `precondition_enforced`
  - `supporting_graph_path`: exact Cypher paths proving the evidence
- Coordinator chooses **"Execute connection pool telemetry check"** instead of the blind restart, preventing a cascading database failure

**The Graph Story:**
```
Investigator recalls:     INC-2026-0901 → Redis standalone pool exhaustion → RESTART → FAILURE
Systems discovers:        checkout-service v2.4.0 → Redis Cluster (pool=64) with circuit breaker
Policy flags:             PROC-REDIS-RESTART requires saturation < 70% (PRECONDITION NOT MET)
Coordinator reconciles:   Reject restart → Choose PROC-INSPECT-POOL (safe, read-only)
```

---

### **Scene 3: Lesson Survived the Session Reset** (~30 seconds)

**Purpose:** Prove cross-session persistent learning — ORBIT actually gets smarter.

1. Select **"Scene 3: Prove the Lesson Survived"**
2. Click **🚀 Run Scene**

**What to look for:**
- The green success banner: **"Cross-Session Memory Adapted"**
- `previous_incident_outcome_recorded: success` — verifies the outcome was committed to FalkorDB
- `new_lesson_persisted_in_graph` — the new `MemoryFact` written to FalkorDB
- `new_session_recommendation` — the system automatically adjusts based on the persisted lesson

**Verification:** After running Scene 3, go to Tab 2 (Graph Explorer), expand MemoryFact nodes, and you'll see the new fact node created in FalkorDB with `SUPERSEDES` or `RELATED_TO` relationships.

---

### **Scene 4: Break the Memory** (~20 seconds)

**Purpose:** Demonstrate optimistic concurrency locking preventing duplicate task claims.

1. Select **"Scene 4: Break the Memory"**
2. Click **🚀 Run Scene**

**What to look for:**
- **Agent 1 (agent-systems): ✅ SUCCESS** — claims task at version=1, version bumped to 2
- **Agent 2 (agent-investigator): 🛑 REJECTED** — same task, same version=1, rejected with precise collision message
- `duplicate_claims_prevented: true`

**The Cypher Lock:**
```cypher
MATCH (t:Task {id: $task_id})
WHERE t.version = $expected_version AND t.status = 'unclaimed'
SET t.status = 'claimed', t.version = t.version + 1
-- Agent 2 also matches t.version = 1 → but version is now 2 → WHERE fails → rejected
```

This is a classic Compare-And-Set (CAS) operation implemented natively in FalkorDB.

---

### **Comparative Benchmark** (~20 seconds)

**Purpose:** Side-by-side proof that graph memory changes the outcome.

1. Go to Tab 5 (Baseline vs ORBIT Comparison)
2. Click **🚀 Run Head-to-Head Comparative Benchmark**

**What to look for:**

| Metric | Without ORBIT | With ORBIT |
|--------|--------------|------------|
| Recommended Action | Restart Redis immediately | Non-destructive connection pool inspection |
| Blast Radius | CRITICAL — causes DB stampede | LOW — read-only diagnostic |
| Config Drift Awareness | ❌ No | ✅ Yes (traversed v2.4 cluster node) |
| Historical Failure Awareness | ❌ No | ✅ Yes (Cypher matched INC-2026-0901) |

---

### **Contradiction Simulator** (~15 seconds)

**Purpose:** Real-time, interactive contradiction detection against live FalkorDB state.

1. Go to Tab 3 (Contradiction & Staleness Inspector)
2. Enter claim: **"Redis cache instance is unresponsive; initiate immediate service restart."**
3. Click **⚡ Test Contradiction Against Graph**

**What happens:**
- The system fetches live topology (`checkout-service` version, `cache_type`, `pool_size`) from FalkorDB
- Fetches historical outcomes from FalkorDB
- Evaluates 3 contradiction patterns and returns graph-backed evidence

---

### **Memory Replay** (~15 seconds)

**Purpose:** Full auditability — reconstruct exactly what the system believed at any decision.

1. Go to Tab 4 (Auditable Memory Replay)
2. Click quick selector **"INC-2026-1016-02"** (or run Scene 2 first)
3. Observe: Decision ID, timestamp, chosen action, active graph facts, agent disagreements, and any lesson learned afterward

---

## 🧪 API Endpoint Exploration (Optional)

Start the API server:
```powershell
.\scripts\start_api.ps1
```

Visit **http://localhost:8000/docs** (Swagger UI) to explore:

| Endpoint | Purpose |
|----------|---------|
| `GET /health` | FalkorDB connectivity check |
| `POST /api/investigate` | Run full 4-agent pipeline |
| `GET /api/scenarios/{scene_id}` | Run scene_1 through scene_4 |
| `GET /api/graph/elements` | Retrieve full graph for visualization |
| `GET /api/comparison` | Comparative benchmark |
| `POST /api/tasks/claim` | Test optimistic locking directly |
| `GET /api/replay/{incident_id}` | Memory replay snapshot |

---

## 📊 Automated Test Suite

```
pytest -v
```

| Test File | What It Verifies |
|-----------|-----------------|
| `test_falkordb_schema.py` | FalkorDB connection, schema seeding, multi-hop Cypher |
| `test_contradiction.py` | Contradiction detection on config drift |
| `test_coordination_tasks.py` | Optimistic concurrency locking |
| `test_memory_supersede.py` | Temporal fact supersession without deletion |
| `test_end_to_end_scenarios.py` | All 4 demo scenes + comparative baseline |
| `test_api_endpoints.py` | FastAPI endpoint correctness |

**Result: 14 passed in ~2 seconds** ✅

---

## 🔑 Why FalkorDB Is Indispensable

| Feature | How FalkorDB Powers It |
|---------|----------------------|
| Cold-start memory | Multi-hop Cypher traversal across `Incident→Episode→Observation→MemoryFact` |
| Contradiction detection | Live topology query (`Service.version`, `cache_type`, `HAS_FACT` edges) |
| Optimistic concurrency | `WHERE t.version = $expected_version` atomic Compare-And-Set |
| Temporal provenance | `(:MemoryFact)-[:SUPERSEDES]->(:MemoryFact)` chain preserves history |
| Decision audit trail | `(:Decision)-[:BASED_ON]->(:Observation)-[:SUPPORTS]->(:MemoryFact)` |
| Cross-session learning | New `MemoryFact` nodes written to graph after verified outcomes |

**Remove FalkorDB → every one of these breaks.**
