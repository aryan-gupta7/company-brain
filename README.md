# 🧠 Company Brain — FalkorDB Hackathon 2026

An AI agent backed by a **Process Knowledge Graph** in FalkorDB that understands how your company works — and proves it with evidence.

**Track 03: Company Brain** | Oct 15-18, 2026 | Online

## Quick Start

```bash
# 1. Start FalkorDB (Docker)
docker run -d --name falkordb-hackathon \
  -p 6380:6379 -p 3001:3000 \
  falkordb/falkordb:latest

# 2. Install dependencies
uv sync

# 3. (Optional) Set LongCat API key for LLM-enhanced responses
export LONGCAT_API_KEY="your-key-here"
# Without the key, the agent falls back to keyword classification

# 4. Run everything (seed graph, generate embeddings, fetch SEC data, run tests, execute demos)
bash run.sh

# 5. Start the web frontend
PYTHONPATH=src uv run python -m web.server
# → http://localhost:8000
```

## What It Does

Ask it anything about your company's operations. It queries the graph, computes the answer, and shows its work.

| Query | What Happens | Graph Operations |
|-------|-------------|------------------|
| "Data breach detected" | Returns incident playbook with deadlines, contacts, legal basis + similar past incidents | Graph traversal (Playbook→Step→Contact) + Vector search (similar incidents) |
| "What can we automate?" | Scores all tasks on feasibility × impact quadrant with annual savings | Graph query (Task + COMPLIES_WITH + DEPENDS_ON + HAS_TASK) |
| "What breaks if CloudHost goes down?" | Traces blast radius, shows affected processes, tasks, at-risk compliance | 3-hop BFS (Vendor→Process→Task→Task) + compliance traversal |
| "GDPR deadlines" | Lists all regulations, finds compliance gaps, shows India-specific requirements | Graph query (Regulations + gap detection) |
| Paste an SOP document | Extracts tasks, dependencies, validates graph, finds critical path | Rule-based parser + cycle detection + DAG longest path |

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                     Web Frontend                         │
│  ┌────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────┐ │
│  │ Chat   │ │ SOP      │ │ Playbook │ │ Graph        │ │
│  │ Panel  │ │ Extract  │ │ Viewer   │ │ Visualization│ │
│  └───┬────┘ └────┬─────┘ └────┬─────┘ └──────┬───────┘ │
│      └───────────┴─────┬──────┴──────────────┘          │
│                        │ REST API (FastAPI)              │
└────────────────────────┼────────────────────────────────┘
                         │
┌────────────────────────┼────────────────────────────────┐
│                   Backend │                              │
│  ┌──────────────────────▼─────────────────────────────┐ │
│  │            CompanyBrainAgent                         │ │
│  │  Intent Classification (keywords + LongCat LLM)      │ │
│  │  → Graph Query → Evidence Assembly → Response        │ │
│  │                                                      │ │
│  │  5 intents: incident_response, automation_assessment │ │
│  │             process_extraction, cascade_analysis     │ │
│  │             compliance_check                         │ │
│  └──────────────────────┬─────────────────────────────┘ │
│                         │                                │
│  ┌──────────────────────▼─────────────────────────────┐ │
│  │  MCP Server (read-only, 8 whitelisted Cypher)       │ │
│  │  + Pure Python scoring + Deterministic deadlines    │ │
│  └──────────────────────┬─────────────────────────────┘ │
│                         │                                │
│  ┌──────────────────────▼─────────────────────────────┐ │
│  │  FalkorDB (graph + vector HNSW + full-text)        │ │
│  │  company_brain graph                                │ │
│  └────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────┘
```

## FalkorDB Graph Schema

### Node Types (9 labels, ~137 nodes)

```
┌──────────────┐     ┌──────────────┐     ┌──────────┐
│   Playbook   │────▶│ StepTemplate │────▶│  Person  │
│ (2 playbooks)│:HAS │  (9 steps)   │:CONT│ (7 people│
│ data_breach  │_STEP │              │ACT  │          │
│ ransomware   │     └──────────────┘     └──────────┘
└──────┬───────┘
       │ :TRIGGERS
       ▼
┌──────────────┐     ┌──────────────┐     ┌──────────┐
│   Incident   │     │    Task      │────▶│Regulation│
│ (102 incidents│     │ (4 tasks)    │:COMPL│(7 regs)  │
│ 100 real SEC │     │              │IES_W │ GDPR     │
│ 8-K Item 1.05│     │              │ITH   │ CCPA     │
└──────────────┘     └──────┬───────┘     │ HIPAA    │
                            │ :DEPENDS_ON │ DPDPA    │
                            ▼             │ CERT-In  │
                     ┌──────────────┐     │ SEC 8-K  │
                     │    Task      │     └──────────┘
                     │ (dependency  │
                     │  chain)      │     ┌──────────┐
                     └──────────────┘     │ Document │
                            ▲             │ (3 docs) │
                            │ :HAS_TASK   └──────────┘
                     ┌──────┴───────┐
                     │   Process    │◀──────┐
                     │ (3 processes)│       │
                     └──────────────┘       │ :PROVIDES
                            ▲               │ _SERVICE
                            │ :OWNS         │ _FOR
                     ┌──────┴───────┐       │
                     │   Person     │───────┘
                     └──────────────┘
                            ▲
                            │ :PROVIDES_SERVICE_FOR
                     ┌──────┴───────┐
                     │   Vendor     │
                     │ (3 vendors)  │
                     └──────────────┘
```

### Relationship Types (8 types)

| Edge | Direction | Properties | Purpose |
|------|-----------|------------|---------|
| `HAS_STEP` | Playbook → StepTemplate | `order`, `amount`, `unit`, `trigger`, `legal_citation` | Playbook structure with deadline metadata |
| `CONTACT` | StepTemplate → Person | — | Who to contact for each step |
| `DEPENDS_ON` | Task → Task | `source_quote`, `confidence` | Task ordering with verbatim evidence |
| `COMPLIES_WITH` | Task → Regulation | `source_quote` | Regulatory compliance mapping |
| `HAS_TASK` | Process → Task | — | Process composition |
| `OWNS` | Person → Process | — | Process ownership |
| `PROVIDES_SERVICE_FOR` | Vendor → Task/Process | — | Vendor dependency |
| `TRIGGERS` | Incident → Playbook | — | Incident-to-playbook mapping |

### FalkorDB Index Usage

| Index Type | Used For | Labels |
|-----------|----------|--------|
| **Graph** (GraphBLAS) | Traversals, BFS, critical path, cycle detection | All 9 labels |
| **Vector** (HNSW, 384-dim cosine) | Similar incident search, similar task matching | Task, Document, Person, Incident, Regulation |
| **Full-text** (RediSearch TF-IDF) | Keyword search on names/descriptions | Task, Document, Playbook, Regulation |
| **Range** | Property filtering | Task.feasibility, Incident.severity, Vendor.risk_score, Regulation.effective_date |

## How FalkorDB Powers Each Intent

### 1. Incident Response
```cypher
-- Graph traversal: Playbook → Step → Contact
MATCH (pb:Playbook {incident_type: $type})-[hs:HAS_STEP]->(step:StepTemplate)
OPTIONAL MATCH (step)-[:CONTACT]->(contact:Person)
RETURN pb.name, step.name, hs.amount, hs.unit, contact.name, ...
ORDER BY hs.order
```
Plus vector search for similar past incidents from 100 real SEC 8-K Item 1.05 filings.

### 2. Automation Assessment
```cypher
-- Graph query: tasks with full relationship context
MATCH (t:Task)
OPTIONAL MATCH (t)-[:COMPLIES_WITH]->(r:Regulation)
OPTIONAL MATCH (t)-[:DEPENDS_ON]->(d:Task)
OPTIONAL MATCH (p:Process)-[:HAS_TASK]->(t)
RETURN t.task_id, t.name, t.structuredness, ..., collect(r.name), collect(d.task_id), p.name
```
Feasibility = `min(structuredness, data_access, 1-decision, 1-exception)` — gated, not weighted.
Impact = `frequency × time_per_exec × labor_rate` — dimensional analysis.

### 3. Cascade Analysis
```cypher
-- Explicit 3-hop BFS (not variable-length paths, for FalkorDB compatibility)
-- Hop 1: Vendor → Process/Task
MATCH (v:Vendor {entity_id: $id})--(connected) WHERE connected:Task OR connected:Process
-- Hop 2: Process → Task
MATCH (p:Process)-[:HAS_TASK]->(t:Task) WHERE p.process_id IN $proc_ids
-- Hop 3: Task → Task (dependencies)
MATCH (t:Task)-[:DEPENDS_ON]->(dep:Task) WHERE t.task_id IN $task_ids
```
Plus compliance context: `Task → COMPLIES_WITH → Regulation` to show at-risk obligations.

### 4. Compliance Check
```cypher
-- Compliance gaps: high-risk tasks with no compliance edges
MATCH (t:Task) WHERE t.compliance_risk > 0.3
OPTIONAL MATCH (t)-[:COMPLIES_WITH]->(r:Regulation)
WITH t, collect(r) AS regs WHERE size(regs) = 0
RETURN t.task_id, t.name, t.compliance_risk
```

### 5. Process Extraction
- Rule-based SOP parser extracts tasks (numbered list regex) and dependencies ("After X, Y" pattern matching with IDF-weighted word scoring)
- Graph validation: cycle detection via strongly connected components (O(V+E)), critical path via DAG longest path
- Every dependency edge carries a verbatim source quote from the SOP

## Project Structure

```
src/
├── core/
│   ├── falkordb_client.py      # FalkorDB connection, 20+ graph queries, cascade BFS
│   ├── deadline_calculator.py   # Deterministic deadline computation (never LLM-generated)
│   ├── automation_scoring.py    # Feasibility × Impact framework with risk gates
│   ├── graph_utils.py           # Graph validation, span-grounding, confidence scoring
│   ├── embeddings.py            # FastEmbed 384-dim embeddings (ONNX, no torch)
│   ├── sop_parser.py            # Rule-based SOP extraction (IDF + prefix-overlap stemming)
│   └── llm_client.py            # LongCat LLM client (optional enhancement)
├── agent/
│   ├── agent.py                 # Single agent, 5 intents, hybrid LLM/keyword routing
│   └── mcp_server.py            # Read-only MCP, 8 whitelisted Cypher templates
├── web/
│   ├── server.py                # FastAPI server with 10 REST endpoints
│   └── static/index.html        # SPA frontend (chat, graph viz, SOP extract, playbook)
├── cli/
│   └── interactive.py           # Interactive CLI (/search, /similar, /cascade, /demo)
├── demo/
│   ├── seed_data.py             # Curated playbooks, tasks, processes, vendors
│   ├── seed_graph.py            # FalkorDB schema seeding (137 nodes, 34+ edges)
│   ├── seed_embeddings.py       # Generate embeddings for all nodes
│   ├── fetch_sec_breaches.py    # SEC EDGAR 8-K Item 1.05 breach ingestion
│   ├── run_demo.py              # Modules 1, 3 (incident + automation)
│   ├── ingestion_demo.py        # Module 2 (document extraction + span-grounding)
│   ├── cascade_demo.py          # Module 4 (blast radius analysis)
│   └── security_demo.py         # Module 6 (security tests)
└── tests/
    ├── test_deadline_calculator.py  # 19 tests
    ├── test_automation_scoring.py   # 20 tests
    ├── test_graph_utils.py          # 21 tests
    └── test_sop_parser.py           # 18 tests
```

## Running Tests

```bash
PYTHONPATH=src uv run python -m pytest src/tests/ -v
# 78 tests, all passing
```

## Web Frontend

```bash
PYTHONPATH=src uv run python -m web.server
# → http://localhost:8000
```

5-tab SPA: **Graph** (vis-network visualization with filters), **SOP Extract** (paste a document, see parsed tasks + deps), **Playbook** (browse incident response playbooks), **Regulations**, **Vendors**.

Quick-actions for all 5 intents. Demo mode banner when FalkorDB is offline. Canvas-based quadrant scatter plot for automation assessment.

## Interactive CLI

```bash
PYTHONPATH=src uv run python -m cli.interactive
```

Commands: `/stats`, `/search`, `/similar`, `/cascade`, `/incidents`, `/vendors`, `/demo`, `/help`

## Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| **Single agent** with intent classification | Simpler than multi-agent + router. Hybrid: keywords + LongCat LLM fallback |
| **Deterministic deadlines** | Never LLM-generated. Pure Python `{amount, unit, trigger}` |
| **Explicit multi-hop BFS** | Not variable-length paths — avoids FalkorDB compatibility issues |
| **StepTemplate label** (not Task) | Prevents ingestion from modifying curated playbooks |
| **Span-grounding** | Every edge carries verbatim source quote, verified by substring |
| **Feasibility = min()** (noisy-AND) | Weakest link matters most. Strengths can't compensate |
| **Impact = hours × rate** | Dimensional analysis, not ordinal scores |
| **Read-only MCP** | 8 whitelisted Cypher templates. No writes. Parameterized queries only |
| **Evidence trail** | Every response includes the exact graph query that produced it |

## Technical Honesty

- All deadlines are **deterministic** (Python computation, never LLM-generated)
- All inputs are **source-labeled** (user-provided, estimated, default, or computed)
- All edges are **span-grounded** (verbatim source quotes)
- Automation math uses **gated feasibility** (no false precision)
- Impact is **hours × rate** (dimensional analysis, not ordinal sums)
- Confidence is **agreement across runs** (consistency, NOT correctness)

## License

MIT
