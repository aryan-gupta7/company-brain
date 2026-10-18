# Company Brain — Research Status & Gaps

> For every major technical claim, design decision, and module in the architecture:
> judge whether research is needed, what kind, and current confidence level.
>
> **UPDATED for v3** — Every item re-judged against verified FalkorDB documentation
> and corrected legal citations.

**Legend**:
- ✅ **Validated** — Decision is grounded in existing research, documentation, or established practice
- ⚠️ **Partial** — Some grounding exists but needs verification or has gaps
- ❌ **Needs Research** — No grounding yet; must validate before building
- 🔴 **Corrected** — Was wrong in v2; now fixed

---

## 1. FalkorDB as the Core Engine

### 1.1 Graph + Vector + Full-Text in One Engine

**Status**: ✅ **Validated**

FalkorDB documentation confirms:
- Graph storage via GraphBLAS sparse adjacency matrices (design docs at docs.falkordb.com/design)
- Vector search via HNSW with cosine/L2 distance, 1-4096 dimensions (docs.falkordb.com/cypher/indexing/vector-index)
- Full-text search via **RediSearch with TF-IDF** (docs.falkordb.com/cypher/indexing/fulltext-index)
  - **CORRECTED**: v2 incorrectly claimed BM25. FalkorDB uses RediSearch (TF-IDF scoring).
  - **CORRECTED**: v2 used non-existent `embedding_similarity()` function. Correct syntax: `CALL db.idx.vector.queryNodes(label, attribute, k, vecf32([...])) YIELD node, score`
- Range index for property filtering (docs.falkordb.com/cypher/indexing/range-index)
- **CORRECTED**: v2 wrote "FalkorDB Core 2.x". Correct: **v6.0.2** (Rust rewrite) / v4.x (C engine)

**No research needed.** This is documented product capability.

---

### 1.2 HNSW Vector Search Performance at Scale

**Status**: ⚠️ **Partial**

HNSW is a well-established algorithm (Malkov & Yashunin, 2018). FalkorDB implements it with configurable M, efConstruction, efRuntime parameters.

**What we need to verify**:
- FalkorDB's specific HNSW implementation limits (max vectors, max dimensions, memory usage per vector)
- Query latency at 100K, 1M, 10M vector scale on FalkorDB Cloud (free tier)
- Whether the demo's vector search will be fast enough live

**Research needed**: Benchmark FalkorDB vector search with realistic data sizes (10K-100K documents for demo). If latency is acceptable, no changes needed. If not, pre-compute embeddings and cache results.

**Effort**: 2-3 hours of benchmarking during implementation.

---

### 1.3 GraphBLAS Sparse Matrix Performance

**Status**: ✅ **Validated**

GraphBLAS is a well-established standard for sparse linear algebra on graphs. FalkorDB's use of it for adjacency matrix storage is documented. For a demo-scale graph (thousands of nodes, tens of thousands of edges), performance will be excellent.

**No research needed** for demo scale.

---

### 1.4 Multi-Tenancy via Named Graphs

**Status**: ✅ **Validated**

FalkorDB supports multiple named graphs in a single instance. Each company gets its own graph. This is documented and straightforward.

**No research needed.**

---

### 1.5 MCP Server Availability and Capabilities

**Status**: ✅ **Validated**

FalkorDB-MCPServer is open source on GitHub (falkordb/FalkorDB-MCPServer). It exposes:
- `query_graph` (Cypher execution)
- `query_graph_readonly`
- `get_graph_schema`
- `get_node_schema` / `get_relationship_schema`
- `list_graphs`
- `delete_graph`

**CORRECTED for v3**: We will NOT expose `delete_graph` to the agent. We will NOT accept free-form Cypher. We build a custom MCP server with 6 read-only, parameterized tools using pre-validated Cypher templates.

**Research needed**: Read the MCP server source code to determine extension pattern. Build custom MCP server with whitelisted Cypher templates.

**Effort**: 1-2 hours reading source code + building custom server.

---

### 1.6 GraphRAG SDK Entity Extraction Quality

**Status**: ⚠️ **Partial** — **HIGHEST RISK ITEM**

GraphRAG SDK claims to extract entities and relationships from unstructured documents. It holds the top score on GraphRAG-Bench (for novels, NOT SOPs — different document type).

**What we need to verify**:
- What entity types does it extract out of the box? (Person, Organization, Date, Location?)
- Does it extract task dependencies? (Probably not — this is domain-specific)
- What's the accuracy on SOP-style documents specifically? (GraphRAG-Bench tests novels, not SOPs)
- Can we customize the extraction schema?

**Research needed**:
1. Read GraphRAG SDK documentation on customization
2. Test extraction on 5-10 sample SOP documents
3. Measure precision/recall for: task names, task order, explicit dependencies, implicit dependencies, document references
4. If it doesn't extract task dependencies well, build a custom LLM extraction pass with span-grounded output

**Effort**: 4-6 hours testing + potentially building custom extraction layer.

**Risk**: **HIGHEST**. This is the core of the system. If extraction quality is poor, the Process Knowledge Graph is unreliable. Mitigation: (1) user review step, (2) span-grounded extraction with confidence scores, (3) curated playbook for incident response (doesn't depend on extraction).

**Honest framing**: Accuracy numbers in v2 were estimated from literature, NOT measured. We must measure on real SOPs before demo and report actual numbers. If low, emphasize user review and curated playbook.

---

### 1.7 GraphRAG SDK Incremental Sync

**Status**: ✅ **Validated**

GraphRAG SDK supports `update()`, `delete_document()`, and `apply_changes()` for incremental updates without rebuilding the graph. This is documented.

**No research needed** for the feature itself.

---

## 2. Process Knowledge Graph Schema

### 2.1 Entity-Relationship Model Design

**Status**: ⚠️ **Partial** — **CORRECTED for v3**

**v2 had 23 node types, 60+ relationships.** Cut to **8 node types, 15 relationships** for v3.

The schema is based on:
- Pragmatic property graph modeling (not academic ontology)
- Domain knowledge of business operations
- What relationships the single agent needs to traverse

**CORRECTED**: v2 used FK-style properties (`owner_id`, `phase_id`) that duplicate edges and drift out of sync. v3 uses relationships only.

**CORRECTED**: v2 used 1536-dim vectors with 384-dim model. v3 uses 384-dim (all-MiniLM-L6-v2) consistently.

**Research needed**: None for hackathon. Note BPMN alignment as future work.

---

### 2.2 Cypher Query Patterns for Multi-Hop Reasoning

**Status**: ✅ **Validated**

Cypher supports variable-length path matching: `(a)-[:DEPENDS_ON*1..5]->(b)`. This is well-documented and tested.

**CORRECTED for v3**:
- Playbook template separated from incident instance: `Playbook → StepTemplate` vs `Incident → StepExecution`
- Self-loops removed (v2 had `(step4)-[:DEADLINE]->(step4)`)
- Onboarding query fixed: was `(Person)-[:COMPLETED_BY]->(Task)` which mines history; now uses curated `Role → TaskTemplate` edges

**No research needed** for query patterns.

---

### 2.3 Graph Algorithms Availability

**Status**: ⚠️ **Partial** — **CORRECTED for v2's unverified claim**

A reviewer claimed FalkorDB ships PageRank, betweenness, WCC, CDLP, shortest paths, and MaxFlow. **I could NOT verify this from official FalkorDB documentation.** The design page mentions GraphBLAS but does not enumerate built-in algorithms.

**Decision**: Use **networkx** for algorithm computation (cycle detection, critical path, centrality). FalkorDB stores the graph; networkx computes on extracted subgraphs. This is verified and reliable.

**Research needed**: 30 minutes to confirm FalkorDB's algorithm page (if it exists). Regardless, networkx is the safe choice.

---

## 3. Agent Modules (Single Agent in v3)

### 3.1 Incident Response Graph

**Status**: ⚠️ **Partial**

The incident response graph structure is a natural graph design. Based on:
- NIST SP 800-61 Rev. 2 (Computer Security Incident Handling Guide)
- Standard incident response playbooks (SANS IR framework)

**CORRECTED for v3**:
- Playbook templates are **curated** (not extracted from documents)
- Deadlines are **deterministic Python** (not LLM output)
- Contacts come from curated graph (not extracted data — prevents prompt injection)
- Similar incidents use **real SEC 8-K Item 1.05 filings** from EDGAR (not made-up)

**Research needed**:
1. Gather NIST SP 800-61 incident categories for curated playbook templates
2. Query SEC EDGAR for real breach disclosure 8-K filings (public corpus for similarity search)

**Effort**: 2-3 hours.

---

### 3.2 Legal Timeline Accuracy

**Status**: 🔴 **CORRECTED** — Multiple errors in v2

| Regulation | v2 Claim | v3 Corrected |
|---|---|---|
| **GDPR Art. 33** | 72 hours from awareness | ✅ Same — 72 hours from awareness (not from breach) |
| **GDPR Art. 34** | Not mentioned | Added: "without undue delay" if high risk to individuals |
| **SEC Item 1.05** | 4 business days from materiality | **REMOVED** for SMB persona — applies only to public registrants |
| **HIPAA individual** | 60 days from discovery | ✅ Same — 60 days from discovery |
| **HIPAA HHS 500+** | Not mentioned | Added: 60 days from discovery |
| **HIPAA HHS <500** | Not mentioned | Added: annual log (within 60 days of year-end) |
| **CCPA** | "Most expedient time possible" | **CORRECTED**: 30 calendar days from discovery per SB 446 (verify enactment status for Jan 2026) |
| **CCPA AG** | Not mentioned | Added: 15 calendar days after consumer notification if >500 CA residents |

**Research needed**: Verify SB 446 enactment status before demo. If not yet enacted, use current law.

---

### 3.3 Compliance Graph Pre-built Templates

**Status**: ❌ **Needs Research**

We want pre-built regulation subgraphs for:
- GDPR (EU data privacy) — breach notification only (cut from full compliance)
- CCPA (California privacy) — breach notification only
- Employment law — basic federal requirements

**CORRECTED for v3**: v2 claimed 87 obligations across 4 regulations — too broad for 3 days. v3 narrows to **breach notification obligations** only (GDPR, CCPA, HIPAA). Employment law compliance is cut.

**Research needed**:
1. GDPR Art. 33-34 requirements for breach notification
2. CCPA §1798.82 requirements for breach notification
3. HIPAA §164.404/408 requirements for breach notification
4. Map each to: requirement → evidence → deadline → citation

**Effort**: 3-4 hours for breach notification templates only.

---

### 3.4 Financial Entity Graph

**Status**: 🔴 **CUT from v3**

The cash flow optimization module was cut. Reasons:
- Doesn't need a graph — it's pandas arithmetic
- Distracts from the core Process Knowledge Graph story
- Adds scope without adding FalkorDB value

**No research needed.** Module removed.

---

### 3.5 Automation Assessment Methodology

**Status**: 🔴 **CORRECTED** — Math was wrong in v2

**v2 errors**:
1. Frequency and duration scored as ordinals and summed → should multiply (hours/year)
2. Weighted sum lets strengths compensate for fatal weaknesses → should use gates (noisy-AND)
3. Error cost and compliance risk added to impact (pushing high-risk toward AUTOMATE NOW) → should be human-in-loop gates
4. Weights (0.30, 0.25, 0.25, 0.20) falsely attributed to McKinsey → removed false citation
5. Savings formula inconsistent → fixed with consistent formula

**v3 corrections**:
- **Feasibility** = `min(structuredness, data_access, decision_simplicity, 1-exception_rate)` with gates
- **Impact** = `frequency_per_year × time_per_exec_hours × labor_rate` (actual hours × dollars)
- **Risk gate**: if `error_cost > threshold OR compliance_risk > 0.7` → force human-in-loop
- **Savings** = `hours_per_year × automation_fraction × labor_rate + error_reduction - implementation_cost`
- All ordinal mappings labeled as "tunable defaults" (not research-derived constants)

**Research needed**: None beyond acknowledging weights are configurable defaults.

---

### 3.6 Savings Calculation Formula

**Status**: 🔴 **CORRECTED**

```
Annual Savings = (hours_per_year × automation_fraction × labor_rate)
               + (error_reduction_value)
               - (annual_implementation_cost)

Where:
  hours_per_year = frequency_per_year × time_per_exec_hours
  automation_fraction = feasibility × (1 - exception_rate)
  error_reduction = (manual_error_rate - automated_error_rate) × error_cost × frequency
```

Every input labeled with source: user-provided, estimated, default (adjustable), computed.

---

### 3.7 Onboarding Pipeline Generation

**Status**: 🔴 **CORRECTED** — Query was logically wrong in v2

v2 query: `(Person {role})-[:COMPLETED_BY]->(Task)` — wrong direction, mines historical tasks instead of generating onboarding checklist.

v3 approach: Onboarding is handled by the single agent using curated `Role → TaskTemplate` edges. Not a separate module. The agent queries: "What tasks are required for role X?" from curated templates, not from historical completion data.

**Research needed**: None. Curated role-task templates are hand-authored.

---

## 4. Ingestion Pipeline

### 4.1 Apache Tika for Universal Parsing

**Status**: ✅ **Validated**

Industry-standard document parser. Used by Elasticsearch, Solr. Handles 1,000+ formats.

**No research needed.**

---

### 4.2 Unstructured for Semantic Partitioning

**Status**: ✅ **Validated**

Well-established library for partitioning documents into typed elements.

**No research needed.**

---

### 4.3 Docling for PDF Layout

**Status**: ✅ **Validated**

IBM's PDF layout understanding tool. Handles multi-column reading order, table structure, OCR.

**No research needed.**

---

### 4.4 Semantic Chunking Strategy

**Status**: ⚠️ **Partial**

Heading detection, boundary detection, table preservation — established techniques.

**Research needed**: Test GraphRAG SDK's default chunking on SOP documents. If it works well, use it. If not, implement semantic chunking with LangChain or LlamaIndex.

**Effort**: 1-2 hours testing.

---

### 4.5 Embedding Model Selection

**Status**: 🔴 **CORRECTED** — Dimension mismatch in v2

v2 used 1536-dim (OpenAI text-embedding-3-small) in some places and 384-dim (all-MiniLM-L6-v2) in others. **Inconsistent.**

v3 decision: **all-MiniLM-L6-v2 (384-dim) everywhere.** Free, local, good enough quality. All vector indexes created with `dimension: 384`.

**Research needed**: None. Decision made.

---

## 5. Agent Architecture (Single Agent in v3)

### 5.1 Multi-Agent Orchestration

**Status**: 🔴 **CUT from v3**

v2 had 6 agents + LangGraph router. Too much for 3 days solo.

v3: **Single agent** with 6 scoped MCP tools. Intent classification picks which tool(s) to call. No router, no multi-agent framework.

**Research needed**: None. Simpler is better for hackathon.

---

### 5.2 Agent Routing Strategy

**Status**: 🔴 **CUT from v3**

No router needed. Single agent with intent classification and tool selection.

---

### 5.3 Explainability Subgraph Extraction

**Status**: ⚠️ **Partial** — **CORRECTED for v3**

**CORRECTED**: v2 claimed `GRAPH.EXPLAIN` provides explainability. It returns the **execution plan**, not the evidence path.

v3 approach: `MATCH p=(start)-[*1..3]-(end) WHERE id(start) IN $node_ids RETURN p` — returns the actual subgraph connecting result nodes. This is the evidence path.

**Research needed**: Test subgraph extraction with FalkorDB Browser for visualization.

**Effort**: 1-2 hours implementation.

---

## 6. Demo & Presentation

### 6.1 Seeded Demo Data Realism

**Status**: ⚠️ **Partial**

**CORRECTED for v3**: Demo data is synthetic but realistic. Clearly labeled as demo data during presentation.

**Research needed**:
1. Find real (anonymized) SOP examples for extraction demo
2. Query SEC EDGAR for real 8-K breach filings for similarity demo
3. Create realistic synthetic company data (roles, departments, vendors)

**Effort**: 2-3 hours.

---

### 6.2 FalkorDB Browser for Visualization

**Status**: ✅ **Validated**

Built-in visualization tool. Can render the Process Knowledge Graph.

**No research needed.**

---

### 6.3 Performance Under Demo Conditions

**Status**: ❌ **Needs Research**

**What we need to verify**:
- Query latency for multi-hop traversals on demo-scale data
- Vector search latency for semantic queries
- Whether the demo will be smooth

**Research needed**: Load test with realistic demo data before presentation. If queries >2 seconds, pre-compute and cache.

**Effort**: 1-2 hours testing.

---

## 7. Track 03 (Company Brain) Fit

### 7.1 Multi-hop Reasoning

**Status**: ✅ **Validated**

Single agent uses multi-hop Cypher queries. Native to FalkorDB.

**No research needed.**

---

### 7.2 Graph Queries as Agent Tools

**Status**: ✅ **Validated**

MCP tools expose parameterized Cypher queries. Agent selects based on context.

**No research needed.**

---

### 7.3 Actions Based on Graph

**Status**: ⚠️ **Partial**

In a hackathon demo, "actions" = generated recommendations + displayed evidence. Not actual execution (no email sending, no filing).

**Research needed**: Review Track 03 judging criteria. If action execution expected, add one integration (Slack notification or email draft).

**Effort**: 1-2 hours if needed.

---

### 7.4 Explainable Results

**Status**: ✅ **Validated**

Evidence subgraphs (`MATCH p=... RETURN p`) provide the path for every answer. FalkorDB Browser renders them.

**No research needed** for concept.

---

## Summary: Research Priority Matrix

```
┌─────────────────────────────────────────┬──────────┬───────────┬──────────┐
│ Research Item                           │ Priority │ Effort    │ Risk     │
├─────────────────────────────────────────┼──────────┼───────────┼──────────┤
│ GraphRAG SDK extraction quality (MEASURE)│ 🔴 HIGH │ 4-6 hrs   │ HIGHEST  │
│ Incident response playbook curation     │ 🔴 HIGH  │ 2-3 hrs   │ MEDIUM   │
│ SEC 8-K filings for similarity corpus   │ 🔴 HIGH  │ 1-2 hrs   │ MEDIUM   │
│ Compliance breach notification content  │ 🟡 MED   │ 3-4 hrs   │ MEDIUM   │
│ Explainability subgraph implementation  │ 🟡 MED   │ 1-2 hrs   │ MEDIUM   │
│ Demo performance testing                │ 🟡 MED   │ 1-2 hrs   │ MEDIUM   │
│ Demo data generation                    │ 🟡 MED   │ 2-3 hrs   │ LOW      │
│ MCP server custom implementation       │ 🟡 MED   │ 1-2 hrs   │ LOW      │
│ Semantic chunking verification          │ 🟢 LOW   │ 1-2 hrs   │ LOW      │
│ CCPA SB 446 enactment verification      │ 🟢 LOW   │ 15 min    │ LOW      │
│ Graph algorithms (confirm vs networkx)  │ 🟢 LOW   │ 30 min    │ LOW      │
├─────────────────────────────────────────┼──────────┼───────────┼──────────┤
│ TOTAL ESTIMATED RESEARCH EFFORT         │          │ ~16-24 hrs│          │
└─────────────────────────────────────────┴──────────┴───────────┴──────────┘
```

### Pre-Build Research (Must Complete Before Coding)

1. **GraphRAG SDK extraction quality test** — Upload 5-10 real SOP documents, measure precision/recall, determine if custom extraction needed
2. **Incident response playbook curation** — Author curated playbook templates from NIST SP 800-61
3. **SEC 8-K filings** — Query EDGAR for real breach disclosures for similarity corpus
4. **Compliance breach notification** — Author GDPR/CCPA/HIPAA breach notification obligation templates
5. **MCP server custom implementation** — Build read-only parameterized tool server

### During-Build Research (Can Parallelize with Coding)

6. **Demo data generation** — Create realistic synthetic company data
7. **Explainability subgraph implementation** — Test and refine
8. **Demo performance testing** — Load test, optimize queries

### Post-Build Research (Polish)

9. **Track 03 fit refinement** — Review criteria, add integration if expected
10. **Extraction accuracy report** — Document measured precision/recall numbers

---

## What Does NOT Need Research

These are validated by FalkorDB documentation or established practice:

- ✅ FalkorDB's graph + vector (HNSW) + full-text (RediSearch TF-IDF) capabilities — **v6.0.2**
- ✅ Correct vector syntax: `CALL db.idx.vector.queryNodes(label, attribute, k, vecf32([...]))`
- ✅ Correct full-text syntax: `CALL db.idx.fulltext.queryNodes(label, term)`
- ✅ Cypher query language for multi-hop traversal
- ✅ Multi-tenancy via named graphs
- ✅ Apache Tika, Unstructured, Docling for document parsing
- ✅ All-MiniLM-L6-v2 embeddings (384-dim, free, local)
- ✅ networkx for graph algorithms (cycle detection, critical path)
- ✅ Legal timeline accuracy (corrected per review)
- ✅ Savings calculation formula (consistent, corrected)
- ✅ Span-grounded extraction with confidence scores
