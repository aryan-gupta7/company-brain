# 🧠 Company Brain — FalkorDB Hackathon 2026

A multi-agent system backed by a **Process Knowledge Graph** in FalkorDB that understands, monitors, and acts on behalf of a company's operations.

**Track 03: Company Brain** | Oct 15-18, 2026 | Online

## Quick Start

```bash
# 1. Start FalkorDB (Docker)
docker run -d --name falkordb-hackathon \
  -p 6380:6379 -p 3001:3000 \
  falkordb/falkordb:latest

# 2. Install dependencies (uv)
uv sync

# 3. Run everything (seed, tests, demos)
bash run.sh

# 4. Or try the interactive CLI
PYTHONPATH=src uv run python -m cli.interactive
```

## Architecture

```
┌─────────────────────────────────────────────────┐
│                  User / Judge                     │
│              "Data breach detected"               │
└──────────────────────┬──────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────┐
│            CompanyBrainAgent                      │
│  Intent Classification → Tool Selection           │
│  → Evidence Assembly → Response                   │
│                                                   │
│  Intents: incident_response, automation_assessment │
│           process_extraction, cascade_analysis     │
│           compliance_check                         │
└──────────────────────┬──────────────────────────┘
                       │
          ┌────────────┼────────────┐
          ▼            ▼            ▼
   ┌──────────┐ ┌──────────┐ ┌──────────────┐
   │ MCP      │ │ Pure     │ │ Deterministic │
   │ Server   │ │ Python   │ │ Deadline      │
   │ (RO)     │ │ Scoring  │ │ Calculator    │
   └────┬─────┘ └──────────┘ └──────────────┘
        │
        ▼
┌─────────────────────────────────────────────────┐
│              FalkorDB (Port 6380)                 │
│  company_brain graph                              │
│                                                   │
│  Nodes: Playbook, StepTemplate, Person, Task,     │
│         Regulation, Process, Document, Incident    │
│                                                   │
│  Edges: HAS_STEP, CONTACT, DEPENDS_ON,            │
│         TRIGGERS, REQUIRES, REFERENCES             │
│                                                   │
│  Indexes: Vector (HNSW, cosine), Full-text        │
│           (RediSearch TF-IDF), Range              │
└─────────────────────────────────────────────────┘
```

## What It Does

### 1. Incident Response (Module 1)
- Detects incident type from natural language
- Traverses curated playbook (NIST SP 800-61 Rev. 2)
- Computes **deterministic deadlines** (never LLM-generated)
- Shows evidence path: Playbook → HAS_STEP → StepTemplate → CONTACT → Person

### 2. Process Extraction (Module 2)
- Parses SOP documents into task graphs
- **Span-grounding**: every edge verified as verbatim source quote
- **Agreement scoring**: multi-run consistency check (flags low-confidence edges)
- Graph validation: cycle detection via SCC, critical path computation

### 3. Automation Assessment (Module 3)
- **Feasibility × Impact** framework with honest math
- Feasibility = `min(structuredness, data_access, 1-decision_complexity, 1-exception_rate)` (gated, not weighted)
- Impact = `frequency × time_per_exec × labor_rate` (dimensional analysis)
- Risk gates: high compliance risk or error cost → force human-in-loop

### 4. Security (Module 4)
- Read-only Cypher (8 whitelisted templates, no free-form)
- Parameterized queries (injection-proof)
- Prompt injection resistance (keyword routing ignores document semantics)

## Project Structure

```
src/
├── core/
│   ├── falkordb_client.py      # FalkorDB connection & query execution
│   ├── deadline_calculator.py   # Deterministic deadline computation
│   ├── automation_scoring.py    # Feasibility × Impact framework
│   └── graph_utils.py           # Graph validation, span-grounding, confidence
├── agent/
│   ├── agent.py                 # Single agent with intent classification
│   └── mcp_server.py            # Read-only parameterized MCP server
├── demo/
│   ├── seed_data.py             # Curated playbooks & demo tasks
│   ├── seed_graph.py            # FalkorDB schema seeding
│   ├── run_demo.py              # Modules 1, 3 (incident + automation)
│   ├── ingestion_demo.py        # Module 2 (document extraction)
│   └── security_demo.py         # Module 4 (security tests)
├── cli/
│   └── interactive.py           # Interactive CLI for judges
└── tests/
    ├── test_deadline_calculator.py  # 19 tests
    ├── test_automation_scoring.py   # 20 tests
    └── test_graph_utils.py          # 21 tests
```

## Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| **Single agent** with intent classification | Simpler than multi-agent + router. Keyword-based, not LLM-for-routing |
| **Deterministic deadlines** | Never LLM-generated. Pure Python with `{amount, unit, trigger}` |
| **StepTemplate label** (not Task) | Prevents ingestion from modifying curated playbooks |
| **Span-grounding** | Every edge carries verbatim source quote, verified by substring |
| **Feasibility = min()** (noisy-AND) | Weakest link matters most. Strengths can't compensate |
| **Impact = hours × rate** | Dimensional analysis, not ordinal scores |
| **Read-only MCP** | 8 whitelisted Cypher templates. No writes. Parameterized |
| **uv** for package management | Fast, deterministic lockfile, modern Python tooling |

## FalkorDB Graph Schema

**Nodes (8 labels):**
- `Playbook` — curated incident response playbooks
- `StepTemplate` — individual playbook steps (NOT Task)
- `Person` — contacts with roles
- `Task` — business process tasks (for automation assessment)
- `Process` — business processes
- `Document` — source SOPs and documents
- `Regulation` — legal regulations (GDPR, CCPA, HIPAA, SEC)
- `Incident` — recorded incidents
- `Vendor` — third-party vendors

**Relationships (10+ types):**
- `HAS_STEP` — Playbook → StepTemplate (with deadline metadata on edge)
- `CONTACT` — StepTemplate → Person
- `DEPENDS_ON` — Task → Task (dependency)
- `TRIGGERS` — Task/Process → Regulation
- `REQUIRES` — Regulation → Task
- `REFERENCES` — Document → Task/Process
- `OWNS` — Person → Process/Task
- `DEPENDS_ON_VENDOR` — Process → Vendor

## Running Tests

```bash
PYTHONPATH=src uv run python -m pytest src/tests/ -v
# 60 tests, all passing
```

## Interactive CLI

```bash
PYTHONPATH=src uv run python -m cli.interactive
```

Try queries like:
- `"data breach detected"` → incident response with deadlines
- `"what can we automate"` → automation assessment
- `"GDPR deadlines"` → compliance check
- `/stats` → graph statistics
- `/demo` → run all demos
- `/help` → available commands

## FalkorDB GUI

Open http://localhost:3001 for the FalkorDB web GUI to explore the graph visually.

## Technical Honesty

- All deadlines are **deterministic** (Python computation, never LLM-generated)
- All inputs are **source-labeled** (user-provided, estimated, default, or computed)
- All edges are **span-grounded** (verbatim source quotes)
- Automation math uses **gated feasibility** (no false precision)
- Impact is **hours × rate** (dimensional analysis, not ordinal sums)
- Confidence is **agreement across runs** (consistency, NOT correctness)
