# Cypher Queries & Graph Algorithms

This document lists every Cypher query and graph algorithm the product depends on. All queries are parameterized (no free-form Cypher) and go through the read-only MCP server.

## MCP Server Templates (8 whitelisted)

These are the only Cypher templates the agent can execute. No free-form Cypher is accepted.

### 1. `get_playbook_steps`
```cypher
MATCH (pb:Playbook {incident_type: $incident_type})-[hs:HAS_STEP]->(step:StepTemplate)
OPTIONAL MATCH (step)-[:CONTACT]->(contact:Person)
RETURN pb.name AS playbook, pb.source_citation AS source,
       step.name AS action, hs.order AS step_order,
       hs.amount AS amount, hs.unit AS unit,
       hs.trigger AS trigger, contact.name AS contact_name,
       contact.role AS contact_role, hs.legal_citation AS legal_basis
ORDER BY hs.order
```
**Used by:** Incident Response intent. Traverses Playbook → Step → Contact → Person.

### 2. `get_entity_connections`
```cypher
MATCH (e {entity_id: $entity_id})
OPTIONAL MATCH (e)-[]-(h1)
OPTIONAL MATCH (h1)-[]-(h2) WHERE h2 <> e
OPTIONAL MATCH (h2)-[]-(h3) WHERE h3 <> h1 AND h3 <> e
WITH DISTINCT COALESCE(h3, h2, h1) AS connected
RETURN labels(connected) AS entity_type,
       connected.name AS name,
       connected.task_id AS task_id,
       connected.entity_id AS entity_id,
       connected.incident_id AS incident_id
LIMIT 50
```
**Used by:** Cascade Analysis. Explicit 3-hop BFS from any entity.

### 3. `get_process_tasks`
```cypher
MATCH (p:Process {process_id: $process_id})-[:HAS_TASK]->(t:Task)
OPTIONAL MATCH (t)-[:DEPENDS_ON]->(d:Task)
RETURN t.task_id, t.name, t.description, t.status,
       collect(d.task_id) AS depends_on
```
**Used by:** Process Extraction. Gets a process with all its tasks and dependencies.

### 4. `get_compliance_requirements`
```cypher
MATCH (r:Regulation {reg_id: $reg_id})-[:REQUIRES]->(req:Task)
RETURN r.name AS regulation, req.name AS requirement,
       r.citation AS legal_citation
```
**Used by:** Compliance Check. Shows what tasks a regulation requires.

### 5. `get_similar_incidents`
```cypher
CALL db.idx.vector.queryNodes('Incident', 'embedding', $k, vecf32($query_vector))
YIELD node, score
RETURN node.incident_id, node.type, node.severity,
       node.detected_at, score
ORDER BY score DESC
LIMIT $k
```
**Used by:** Incident Response. HNSW vector similarity search against 100 real SEC filings.

### 6. `get_tasks_by_feasibility`
```cypher
MATCH (t:Task)
WHERE t.automation_feasibility >= $min_feasibility
RETURN t.task_id, t.name, t.automation_feasibility,
       t.automation_impact, t.hours_per_year
ORDER BY t.automation_feasibility DESC
LIMIT $limit
```
**Used by:** Automation Assessment. Range index query on feasibility score.

### 7. `search_tasks_fulltext`
```cypher
CALL db.idx.fulltext.queryNodes('Task', $term)
YIELD node, score
RETURN node.task_id, node.name, node.description, score
ORDER BY score DESC
LIMIT $limit
```
**Used by:** Full-text search. RediSearch TF-IDF keyword matching.

### 8. `get_evidence_path`
```cypher
MATCH (n)-[r]-(m)
WHERE n.task_id IN $node_ids
   OR n.entity_id IN $node_ids
   OR n.reg_id IN $node_ids
   OR n.incident_id IN $node_ids
   OR n.process_id IN $node_ids
RETURN COALESCE(n.name, n.task_id, n.entity_id, n.reg_id, n.incident_id, n.process_id) AS src,
       COALESCE(m.name, m.task_id, m.entity_id, m.reg_id, n.incident_id, n.process_id) AS dst,
       type(r) AS rel_type
LIMIT 20
```
**Used by:** Evidence trail. Shows direct neighbors of result nodes.

## Graph-Powered Agent Queries (in `falkordb_client.py`)

These queries are called directly by the agent handlers:

### Automation: Tasks with Full Graph Context
```cypher
MATCH (t:Task)
OPTIONAL MATCH (t)-[:COMPLIES_WITH]->(r:Regulation)
OPTIONAL MATCH (t)-[:DEPENDS_ON]->(d:Task)
OPTIONAL MATCH (p:Process)-[:HAS_TASK]->(t)
RETURN t.task_id, t.name, t.description,
       t.frequency_per_year, t.time_per_exec_hours, t.labor_rate_dollars,
       t.structuredness, t.data_accessibility, t.decision_complexity,
       t.exception_rate, t.error_cost_dollars, t.compliance_risk,
       t.implementation_cost_annual,
       collect(DISTINCT r.name) AS regulations,
       collect(DISTINCT r.jurisdiction) AS regulation_jurisdictions,
       collect(DISTINCT d.task_id) AS depends_on,
       p.name AS process_name
ORDER BY t.name
```

### Cascade: Multi-Hop BFS (Explicit, Not Variable-Length)
```cypher
-- Hop 1: Vendor → direct connections
MATCH (v:Vendor {entity_id: $entity_id})--(connected)
WHERE connected:Task OR connected:Process
RETURN DISTINCT labels(connected) AS entity_type,
       COALESCE(connected.task_id, connected.process_id) AS id,
       connected.name AS name

-- Hop 2: Process → Task (from processes found in hop 1)
MATCH (p:Process)-[:HAS_TASK]->(t:Task)
WHERE p.process_id IN $proc_ids
RETURN DISTINCT labels(t) AS entity_type, t.task_id AS id, t.name AS name

-- Hop 3: Task → Task (DEPENDS_ON chain)
MATCH (t:Task)-[d:DEPENDS_ON]->(dep:Task)
WHERE t.task_id IN $task_ids
RETURN DISTINCT labels(dep) AS entity_type, dep.task_id AS id, dep.name AS name
```

### Cascade: Vendor Risk with Compliance Context
```cypher
MATCH (v:Vendor {entity_id: $vendor_id})-[:PROVIDES_SERVICE_FOR]->(target)
OPTIONAL MATCH (target)-[:HAS_TASK]->(t:Task)
OPTIONAL MATCH (t)-[:COMPLIES_WITH]->(r:Regulation)
WITH v, target, t, r,
     CASE WHEN target:Process THEN 'Process' ELSE 'Task' END AS target_type
RETURN target.name AS entity_name, target_type,
       t.name AS task_name, r.name AS regulation,
       r.jurisdiction AS jurisdiction, t.compliance_risk AS task_risk
ORDER BY target_type, target.name
```

### Compliance: Gap Detection
```cypher
-- Tasks with high compliance risk but no compliance edges
MATCH (t:Task)
WHERE t.compliance_risk > 0.3
OPTIONAL MATCH (t)-[:COMPLIES_WITH]->(r:Regulation)
WITH t, collect(r) AS regs
WHERE size(regs) = 0
RETURN t.task_id, t.name, t.compliance_risk AS risk, t.description
ORDER BY t.compliance_risk DESC
```

### Compliance: Regulation Impact
```cypher
-- What tasks/processes are affected by a regulation
MATCH (r:Regulation {reg_id: $reg_id})<-[:COMPLIES_WITH]-(t:Task)
OPTIONAL MATCH (p:Process)-[:HAS_TASK]->(t)
OPTIONAL MATCH (t)-[:DEPENDS_ON]->(downstream:Task)
RETURN t.task_id, t.task_name, t.compliance_risk,
       p.name AS process_name, collect(DISTINCT downstream.name) AS downstream_tasks
ORDER BY t.compliance_risk DESC
```

### Process: Critical Path (Explicit 4-Hop)
```cypher
MATCH (p:Process {process_id: $process_id})-[:HAS_TASK]->(t:Task)
OPTIONAL MATCH (t)-[:DEPENDS_ON]->(d1:Task)
OPTIONAL MATCH (d1)-[:DEPENDS_ON]->(d2:Task)
OPTIONAL MATCH (d2)-[:DEPENDS_ON]->(d3:Task)
OPTIONAL MATCH (d3)-[:DEPENDS_ON]->(d4:Task)
WITH t,
     CASE WHEN d4 IS NOT NULL THEN 4
          WHEN d3 IS NOT NULL THEN 3
          WHEN d2 IS NOT NULL THEN 2
          WHEN d1 IS NOT NULL THEN 1
          ELSE 0 END AS depth,
     [x IN [d1, d2, d3, d4] WHERE x IS NOT NULL | x.name] AS chain
RETURN t.task_id, t.task_name, t.time_per_exec_hours,
       depth AS dependency_depth, chain AS dependency_chain
ORDER BY depth DESC, t.time_per_exec_hours DESC
```

### Vector Search: Similar Incidents (SEC EDGAR)
```cypher
CALL db.idx.vector.queryNodes('Incident', 'embedding', $k, vecf32($qv))
YIELD node, score
RETURN node.incident_id, node.company_name, node.type, node.severity, score
ORDER BY score DESC
LIMIT $k
```

### Vector Search: Similar Tasks with Graph Context
```cypher
CALL db.idx.vector.queryNodes('Task', 'embedding', $k, vecf32($qv))
YIELD node, score
WHERE node.task_id <> $exclude_id
OPTIONAL MATCH (node)-[:COMPLIES_WITH]->(r:Regulation)
RETURN node.task_id, node.name, score,
       collect(DISTINCT r.name) AS shared_regulations
ORDER BY score DESC
```

## Graph Algorithms (in `graph_utils.py`)

### Cycle Detection — Strongly Connected Components
```python
def detect_cycles(G: nx.DiGraph) -> List[set]:
    """O(V+E) via SCC. A cycle exists if any SCC has >1 node."""
    sccs = nx.strongly_connected_components(G)
    return [scc for scc in sccs if len(scc) > 1]
```

### Critical Path — DAG Longest Path
```python
def find_critical_path(G: nx.DiGraph) -> Tuple[list, float]:
    """Longest path by duration using dag_longest_path with edge weights."""
    # Converts node durations to edge weights: edge (u,v) gets duration of u
```

### Span-Grounding Verification
```python
def verify_span_grounding(dep: dict, sop_text: str) -> bool:
    """Verify that a dependency's source quote is a verbatim substring of the SOP."""
    # Checks quote appears at stated offset in source text
```

### Process Validation Pipeline
```python
def validate_process_graph(tasks, deps) -> dict:
    """Build graph → detect cycles → compute critical path → return validation."""
    G = build_task_graph(tasks, deps)
    cycles = detect_cycles(G)
    if cycles:
        return {'valid': False, 'cycles': cycles}
    path, length = find_critical_path(G)
    return {'valid': True, 'critical_path': path, 'path_length_hours': length}
```

### Downstream Impact Computation
```python
def compute_downstream_impact(G: nx.DiGraph, source_id: str) -> dict:
    """BFS from source to find all downstream affected tasks."""
```

## Why Explicit Multi-Hop BFS?

FalkorDB can error on variable-length paths (`[*1..3]`) with certain relationship property configurations. All multi-hop queries use explicit BFS:

```cypher
-- Instead of: MATCH (t)-[:DEPENDS_ON*1..4]->(dep)
-- We use:
OPTIONAL MATCH (t)-[:DEPENDS_ON]->(d1)
OPTIONAL MATCH (d1)-[:DEPENDS_ON]->(d2)
OPTIONAL MATCH (d2)-[:DEPENDS_ON]->(d3)
OPTIONAL MATCH (d3)-[:DEPENDS_ON]->(d4)
```

This is verbose but predictable — O(hops) queries, no risk of FalkorDB compatibility issues.

## Index Strategy

| Index | Type | Labels | Properties | Used For |
|-------|------|--------|------------|----------|
| Vector | HNSW (cosine) | Task, Document, Person, Incident, Regulation | embedding (384-dim) | Semantic similarity search |
| Full-text | RediSearch TF-IDF | Task, Document, Playbook, Regulation | name, description | Keyword search |
| Range | B-tree | Task, Incident, Regulation, Vendor | compliance_risk, detected_at, severity, risk_score, effective_date | Property filtering |
