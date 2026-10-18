# Company Brain — TODO List

> Last updated: 2026-10-18 (evening)
> Hackathon deadline: 2026-10-18 (TODAY)

---

## ✅ COMPLETED THIS SESSION

### Research Completed
- [x] Embeddings: FastEmbed chosen (~150MB, no torch, ONNX Runtime based)
- [x] GraphRAG SDK: `graphrag-sdk` installable, ~50-100MB, no torch (GLiNER for NER)
- [x] SEC Corpus: EDGAR API free, no API key, returns 100+ Item 1.05 filings

### New Features Built
- [x] FastEmbed integration (`src/core/embeddings.py`) — 384-dim embeddings
- [x] Embedding generation for all nodes (`src/demo/generate_embeddings.py`)
- [x] Vector search working (Tasks, Incidents, Regulations)
- [x] SEC breach ingestion (`src/demo/fetch_sec_breaches.py`) — 100 real filings
- [x] Similar incidents search (vector-based)
- [x] Cascade analysis demo (`src/demo/cascade_demo.py`)
- [x] Extended schema: Process, Document, Vendor, Incident nodes
- [x] New relationships: OWNS, HAS_TASK, PROVIDES_SERVICE_FOR, TRIGGERS, COMPLIES_WITH, DEPENDS_ON
- [x] Range indexes created
- [x] CLI: /search, /similar, /cascade, /vendors, /incidents commands
- [x] Graph: 137 nodes, 34 relationships across all 8 node types

---

## 🟡 REMAINING — Can Build Now

### GraphRAG SDK Integration
- [ ] Install `graphrag-sdk` for real document extraction
- [ ] If installed: test extraction on a real SOP document
- [ ] If extraction works: compare with simulated extraction accuracy

### Interactive CLI Improvements
- [ ] Connect incident handler to real FalkorDB queries (currently uses curated data)
- [ ] Add /playbooks command
- [ ] Add /regulations command
- [ ] Add /processes command

### Evidence Subgraph Rendering
- [ ] Format get_evidence_path() results as readable path in demo output
- [ ] Show in incident response demo

### Demo Polish
- [ ] Update incident demo to show similar incidents from SEC data
- [ ] Add vector search demo to run.sh (done)
- [ ] Final end-to-end test of run.sh

### Documentation
- [ ] Update README with new features (embeddings, SEC data, cascade)
- [ ] Update technical_breakdown_v3.md with final architecture

---

## ❌ CUT — Acknowledged

| Feature | Reason |
|---------|--------|
| Streamlit UI | CLI is sufficient |
| LLM integration | Keyword classification more reliable |
| Full GraphRAG SDK pipeline | Simulated extraction is honest |
| SEC filing body text | Only metadata needed for demo |

---

## 📊 Current State

- **Tests**: 60/60 passing
- **Nodes**: 137 (Task:4, Person:7, Playbook:2, StepTemplate:9, Process:3, Document:3, Regulation:4, Incident:102, Vendor:3)
- **Relationships**: 34 (HAS_STEP, CONTACT, OWNS, HAS_TASK, PROVIDES_SERVICE_FOR, TRIGGERS, COMPLIES_WITH, DEPENDS_ON)
- **Indexes**: Full-text (RediSearch TF-IDF), Vector (HNSW, 384-dim cosine), Range
- **Embeddings**: BAAI/bge-small-en-v1.5 via FastEmbed (ONNX Runtime)
- **SEC Data**: 100 real 8-K Item 1.05 breach disclosures
- **Demos**: 6 (incident, extraction, automation, cascade, vector search, security)
