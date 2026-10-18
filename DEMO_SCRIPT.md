# Demo Video Script (5 minutes)

## Pre-recording Setup
- Terminal at 1920x1080, font size 16
- Browser open to http://localhost:8000
- FalkorDB running (docker ps shows falkordb-hackathon)
- Run `bash run.sh` to seed fresh data first

---

## Scene 1: Introduction (0:00–0:30)

**Terminal:** Show FalkorDB running
```bash
docker ps | grep falkordb
```

**Say:** "This is Company Brain — an AI agent for your company's operations. It's backed by a Process Knowledge Graph in FalkorDB. Every answer it gives traces back to a real graph traversal."

**Browser:** Show the web frontend at http://localhost:8000
- Point out: chat panel, graph visualization, 5 tabs

---

## Scene 2: Incident Response (0:30–1:15)

**Browser:** Click "🚨 Data Breach" quick-action

**Say:** "When a breach happens, the agent traverses the incident response graph. It pulls playbook steps from FalkorDB, computes deterministic deadlines — never LLM-generated — and shows who to contact and the legal basis for each step."

**Point out:**
- Steps with deadlines computed from edge metadata
- Contacts with roles
- Legal basis citations
- Similar incidents from vector search against real SEC filings
- Evidence trail showing the exact graph query

---

## Scene 3: Automation Assessment (1:15–2:00)

**Browser:** Click "🤖 Automation" quick-action

**Say:** "The agent queries the graph for all tasks with their compliance context and dependency structure, then scores each one on feasibility times impact. Feasibility uses min-gating — a chain is only as strong as its weakest link."

**Point out:**
- Scores table with feasibility, impact, quadrant, annual savings
- The quadrant scatter plot — bubbles sized by savings, colored by quadrant
- Graph context showing process, regulations, downstream deps per task
- Evidence trail

---

## Scene 4: Cascade Analysis (2:00–2:45)

**Browser:** Click "💥 Cascade" quick-action

**Say:** "What breaks if a vendor goes down? The agent does a 3-hop BFS through the graph — vendor to process to task to downstream tasks — then layers on compliance context to show not just what breaks, but what regulatory obligations are at risk."

**Point out:**
- Blast radius count
- Affected processes and tasks as tags
- Compliance at risk: entity → task → regulation
- Vendor list if no vendor specified (clickable to re-query)

---

## Scene 5: SOP Extraction (2:45–3:30)

**Browser:** Click "📄 SOP Extract" tab

**Say:** "Paste any SOP document and the rule-based parser extracts tasks and dependencies. It uses IDF-weighted word matching with prefix-overlap stemming — no ML required, fully deterministic."

**Action:** Click "📋 Invoice SOP" button, then "🔍 Extract"

**Point out:**
- Tasks extracted with IDs
- Dependencies with source quotes (verbatim from the document)
- Validation result: graph valid, no cycles
- Critical path computation
- Pipeline: Parse → Extract → Span Verify → Validate → User Review

---

## Scene 6: Graph Visualization (3:30–4:15)

**Browser:** Click "🕸️ Graph" tab

**Say:** "The graph is the brain. Here's the full Process Knowledge Graph — 9 node types, 8 relationship types, ~137 nodes."

**Action:**
- Toggle physics on/off
- Uncheck some filters (e.g., Person, Document) → nodes disappear
- Click a node → detail panel shows all properties

**Point out:**
- Color coding by node type
- Interactive physics simulation
- Label filtering
- Click-to-detail

---

## Scene 7: Compliance + Summary (4:15–5:00)

**Browser:** Click "⚖️ GDPR" quick-action

**Say:** "Compliance checking pulls regulations from the graph, finds gaps — tasks with high compliance risk but no compliance edges — and shows India-specific requirements with legal citations."

**Point out:**
- Regulations by jurisdiction
- Compliance gaps list
- India framework details with deadlines

**Terminal:** Show graph stats
```bash
PYTHONPATH=src uv run python -c "
from core.falkordb_client import CompanyBrainDB
db = CompanyBrainDB(port=6380)
stats = db.get_graph_stats()
print(f'{sum(stats[\"nodes\"].values())} nodes, {sum(stats[\"relationships\"].values())} relationships')
for label, count in stats['nodes'].items():
    if count > 0: print(f'  {label}: {count}')
"
```

**Say:** "Company Brain — the graph is the brain, the agent is the interface, the evidence is the proof. Thank you."

---

## End Screen
- Show README on GitHub (once repo is up)
- FalkorDB GUI at http://localhost:3001
- Link to submission
