"""FalkorDB connection and query execution for Company Brain.

Read-only by default. Uses parameterized Cypher queries.
Default port 6380 to avoid conflict with local Redis on 6379.
"""

import falkordb
from typing import List, Dict, Optional, Any


class CompanyBrainDB:
    """FalkorDB wrapper for Company Brain."""

    def __init__(self, host: str = 'localhost', port: int = 6380,
                 graph_name: str = 'company_brain'):
        self.client = falkordb.FalkorDB(host=host, port=port)
        self.graph_name = graph_name
        self.graph = self.client.select_graph(graph_name)

    def query(self, cypher: str, params: dict = None) -> List[list]:
        """Execute a Cypher query. Returns result set as list of lists."""
        result = self.graph.query(cypher, params or {})
        return result.result_set

    def create_vector_indexes(self):
        """Create vector indexes for semantic search (384-dim, cosine)."""
        labels = ['Task', 'Document', 'Person', 'Incident', 'Regulation']
        for label in labels:
            try:
                self.graph.query(
                    f"CREATE VECTOR INDEX FOR (n:{label}) ON (n.embedding) "
                    f"OPTIONS {{dimension: 384, similarityFunction: 'cosine'}}"
                )
            except Exception:
                pass  # Index may already exist

    def update_node_embedding(self, label: str, node_id_prop: str, node_id: str, embedding: list):
        """Update the embedding property on a node."""
        self.graph.query(
            f"""
            MATCH (n:{label} {{ {node_id_prop}: $node_id }})
            SET n.embedding = vecf32($embedding)
            """,
            {'node_id': node_id, 'embedding': embedding}
        )

    def create_fulltext_indexes(self):
        """Create full-text indexes for keyword search (RediSearch TF-IDF)."""
        for label in ['Task', 'Document', 'Playbook', 'Regulation']:
            try:
                self.graph.query(
                    f"CREATE FULLTEXT INDEX FOR (n:{label}) ON (n.name, n.description)"
                )
            except Exception:
                pass

    def seed_playbooks(self, playbooks: list):
        """Seed curated playbook data into the graph."""
        for pb in playbooks:
            # Create playbook node
            self.graph.query(
                """
                MERGE (pb:Playbook {playbook_id: $playbook_id})
                SET pb.name = $name,
                    pb.incident_type = $incident_type,
                    pb.version = $version,
                    pb.last_reviewed = $last_reviewed,
                    pb.source_citation = $source_citation
                """,
                {
                    'playbook_id': pb['playbook_id'],
                    'name': pb['name'],
                    'incident_type': pb['incident_type'],
                    'version': pb['version'],
                    'last_reviewed': pb['last_reviewed'],
                    'source_citation': pb['source_citation'],
                }
            )

            for step in pb['steps']:
                # Create StepTemplate node
                self.graph.query(
                    """
                    MERGE (s:StepTemplate {step_id: $step_id})
                    SET s.name = $name,
                        s.contact_role = $contact_role
                    """,
                    {
                        'step_id': step['step_id'],
                        'name': step['name'],
                        'contact_role': step['contact_role'],
                    }
                )

                # Create HAS_STEP edge with deadline metadata
                self.graph.query(
                    """
                    MATCH (pb:Playbook {playbook_id: $playbook_id})
                    MATCH (s:StepTemplate {step_id: $step_id})
                    MERGE (pb)-[r:HAS_STEP]->(s)
                    SET r.order = $order,
                        r.amount = $amount,
                        r.unit = $unit,
                        r.trigger = $trigger,
                        r.legal_citation = $legal_citation
                    """,
                    {
                        'playbook_id': pb['playbook_id'],
                        'step_id': step['step_id'],
                        'order': step['order'],
                        'amount': step['amount'],
                        'unit': step['unit'],
                        'trigger': step['trigger'],
                        'legal_citation': step.get('legal_citation', ''),
                    }
                )

                # Create Person node and CONTACT edge
                contact_name = step.get('contact', '')
                contact_role = step.get('contact_role', '')
                if contact_name:
                    person_id = f"p_{contact_name.lower().replace(' ', '_')}"
                    self.graph.query(
                        """
                        MERGE (p:Person {person_id: $person_id})
                        SET p.name = $name, p.role = $role
                        """,
                        {'person_id': person_id, 'name': contact_name, 'role': contact_role}
                    )
                    self.graph.query(
                        """
                        MATCH (s:StepTemplate {step_id: $step_id})
                        MATCH (p:Person {person_id: $person_id})
                        MERGE (s)-[:CONTACT]->(p)
                        """,
                        {'step_id': step['step_id'], 'person_id': person_id}
                    )

    def seed_tasks(self, tasks: list):
        """Seed demo tasks into the graph."""
        for task in tasks:
            self.graph.query(
                """
                MERGE (t:Task {task_id: $task_id})
                SET t.name = $name,
                    t.description = $description,
                    t.frequency_per_year = $frequency_per_year,
                    t.time_per_exec_hours = $time_per_exec_hours,
                    t.labor_rate_dollars = $labor_rate_dollars,
                    t.structuredness = $structuredness,
                    t.data_accessibility = $data_accessibility,
                    t.decision_complexity = $decision_complexity,
                    t.exception_rate = $exception_rate,
                    t.error_cost_dollars = $error_cost_dollars,
                    t.compliance_risk = $compliance_risk,
                    t.implementation_cost_annual = $implementation_cost_annual
                """,
                {**task, 'implementation_cost_annual': task.get('implementation_cost_annual', 0)}
            )

    def seed_regulations(self, regulations: list):
        """Seed regulation nodes."""
        for reg in regulations:
            self.graph.query(
                """
                MERGE (r:Regulation {reg_id: $reg_id})
                SET r.name = $name,
                    r.jurisdiction = $jurisdiction,
                    r.citation = $citation,
                    r.effective_date = $effective_date,
                    r.breach_notification_hours = $breach_notification_hours,
                    r.max_penalty_inr = $max_penalty_inr,
                    r.status = $status
                """,
                {**reg, 'breach_notification_hours': reg.get('breach_notification_hours'),
                 'max_penalty_inr': reg.get('max_penalty_inr'),
                 'status': reg.get('status')}
            )

    def seed_processes(self, processes: list, tasks: list):
        """Seed process nodes and link to tasks via HAS_TASK."""
        for proc in processes:
            self.graph.query(
                """
                MERGE (p:Process {process_id: $process_id})
                SET p.name = $name,
                    p.domain = $domain,
                    p.description = $description
                """,
                {
                    'process_id': proc['process_id'],
                    'name': proc['name'],
                    'domain': proc['domain'],
                    'description': proc['description'],
                }
            )
            # Link to owner
            if proc.get('owner_person_id'):
                self.graph.query(
                    """
                    MATCH (p:Process {process_id: $process_id})
                    MATCH (person:Person {person_id: $person_id})
                    MERGE (person)-[:OWNS]->(p)
                    """,
                    {'process_id': proc['process_id'], 'person_id': proc['owner_person_id']}
                )
            # Link to tasks
            for task_id in proc.get('task_ids', []):
                self.graph.query(
                    """
                    MATCH (p:Process {process_id: $process_id})
                    MATCH (t:Task {task_id: $task_id})
                    MERGE (p)-[:HAS_TASK]->(t)
                    """,
                    {'process_id': proc['process_id'], 'task_id': task_id}
                )

    def seed_documents(self, documents: list):
        """Seed document nodes."""
        for doc in documents:
            self.graph.query(
                """
                MERGE (d:Document {doc_id: $doc_id})
                SET d.title = $title,
                    d.type = $type,
                    d.format = $format
                """,
                doc
            )

    def seed_vendors(self, vendors: list):
        """Seed vendor/service nodes and link to tasks/processes."""
        for vendor in vendors:
            self.graph.query(
                """
                MERGE (v:Vendor {entity_id: $entity_id})
                SET v.name = $name,
                    v.type = $type,
                    v.contact_info = $contact_info,
                    v.risk_score = $risk_score,
                    v.status = $status
                """,
                vendor
            )
            # Link to tasks
            for task_id in vendor.get('provides_for_task_ids', []):
                self.graph.query(
                    """
                    MATCH (v:Vendor {entity_id: $entity_id})
                    MATCH (t:Task {task_id: $task_id})
                    MERGE (v)-[:PROVIDES_SERVICE_FOR]->(t)
                    """,
                    {'entity_id': vendor['entity_id'], 'task_id': task_id}
                )
            # Link to processes
            for proc_id in vendor.get('provides_for_process_ids', []):
                self.graph.query(
                    """
                    MATCH (v:Vendor {entity_id: $entity_id})
                    MATCH (p:Process {process_id: $process_id})
                    MERGE (v)-[:PROVIDES_SERVICE_FOR]->(p)
                    """,
                    {'entity_id': vendor['entity_id'], 'process_id': proc_id}
                )

    def seed_incidents(self, incidents: list):
        """Seed incident nodes and link to playbooks."""
        for inc in incidents:
            self.graph.query(
                """
                MERGE (i:Incident {incident_id: $incident_id})
                SET i.type = $type,
                    i.severity = $severity,
                    i.detected_at = $detected_at,
                    i.status = $status
                """,
                inc
            )
            # Link to playbook
            if inc.get('triggers_playbook_id'):
                self.graph.query(
                    """
                    MATCH (i:Incident {incident_id: $incident_id})
                    MATCH (pb:Playbook {playbook_id: $playbook_id})
                    MERGE (i)-[:TRIGGERS]->(pb)
                    """,
                    {'incident_id': inc['incident_id'], 'playbook_id': inc['triggers_playbook_id']}
                )

    def seed_people(self, people: list):
        """Seed additional people."""
        for person in people:
            self.graph.query(
                """
                MERGE (p:Person {person_id: $person_id})
                SET p.name = $name,
                    p.role = $role,
                    p.department = $department
                """,
                person
            )

    def seed_task_dependencies(self, dependencies: list):
        """Seed DEPENDS_ON relationships between tasks."""
        for dep in dependencies:
            self.graph.query(
                """
                MATCH (a:Task {task_id: $from_id})
                MATCH (b:Task {task_id: $to_id})
                MERGE (a)-[r:DEPENDS_ON]->(b)
                SET r.source_quote = $source_quote,
                    r.confidence = $confidence
                """,
                {
                    'from_id': dep['from'],
                    'to_id': dep['to'],
                    'source_quote': dep.get('source_quote', ''),
                    'confidence': dep.get('confidence', 0.5),
                }
            )

    def seed_compliance_mappings(self, mappings: list):
        """Seed COMPLIES_WITH relationships between tasks and regulations."""
        for mapping in mappings:
            self.graph.query(
                """
                MATCH (t:Task {task_id: $task_id})
                MATCH (r:Regulation {reg_id: $reg_id})
                MERGE (t)-[c:COMPLIES_WITH]->(r)
                SET c.source_quote = $source_quote
                """,
                {
                    'task_id': mapping['task_id'],
                    'reg_id': mapping['reg_id'],
                    'source_quote': mapping.get('source_quote', ''),
                }
            )

    def create_range_indexes(self):
        """Create range indexes for property filtering."""
        index_definitions = [
            ("Task", "due_date"),
            ("Task", "automation_feasibility"),
            ("Task", "compliance_risk"),
            ("Incident", "detected_at"),
            ("Incident", "severity"),
            ("Regulation", "effective_date"),
            ("Vendor", "risk_score"),
        ]
        for label, prop in index_definitions:
            try:
                self.graph.query(
                    f"CREATE RANGE INDEX FOR (n:{label}) ON (n.{prop})"
                )
            except Exception:
                pass

    def get_cascade_impact(self, entity_id: str, max_depth: int = 3) -> list:
        """Get all entities downstream of a vendor/service (blast radius).

        Uses explicit multi-hop queries instead of variable-length paths
        to avoid FalkorDB's 'unhandled type in inlined properties' error.
        """
        results = []
        visited = {entity_id}

        # Hop 1: direct connections (Vendor → Process or Vendor → Task)
        result = self.graph.query(
            """
            MATCH (v:Vendor {entity_id: $entity_id})--(connected)
            WHERE connected:Task OR connected:Process
            RETURN DISTINCT labels(connected) AS entity_type,
                   COALESCE(connected.task_id, connected.process_id) AS id,
                   connected.name AS name
            """,
            {'entity_id': entity_id}
        )
        for row in result.result_set or []:
            if row[1] not in visited:
                visited.add(row[1])
                results.append(row)

        # Hop 2: Process → Task (from processes found in hop 1)
        proc_ids = [row[1] for row in results if row[1] and row[1].startswith('proc_')]
        if proc_ids:
            result = self.graph.query(
                """
                MATCH (p:Process)-[:HAS_TASK]->(t:Task)
                WHERE p.process_id IN $proc_ids
                RETURN DISTINCT labels(t) AS entity_type,
                       t.task_id AS id,
                       t.name AS name
                """,
                {'proc_ids': proc_ids}
            )
            for row in result.result_set or []:
                if row[1] not in visited:
                    visited.add(row[1])
                    results.append(row)

        # Hop 3: Task → Task (DEPENDS_ON)
        task_ids = [row[1] for row in results if row[1] and row[1].startswith('t_')]
        if task_ids:
            result = self.graph.query(
                """
                MATCH (t:Task)-[d:DEPENDS_ON]->(dep:Task)
                WHERE t.task_id IN $task_ids
                RETURN DISTINCT labels(dep) AS entity_type,
                       dep.task_id AS id,
                       dep.name AS name
                """,
                {'task_ids': task_ids}
            )
            for row in result.result_set or []:
                if row[1] not in visited:
                    visited.add(row[1])
                    results.append(row)

        return results

    def get_process_with_tasks(self, process_id: str) -> list:
        """Get a process and all its tasks."""
        result = self.graph.query(
            """
            MATCH (p:Process {process_id: $process_id})-[:HAS_TASK]->(t:Task)
            OPTIONAL MATCH (t)-[:COMPLIES_WITH]->(r:Regulation)
            RETURN p.name AS process_name, t.task_id, t.name AS task_name,
                   t.description, collect(r.name) AS regulations
            ORDER BY t.name
            """,
            {'process_id': process_id}
        )
        return result.result_set or []

    def get_task_dependencies(self, task_id: str) -> list:
        """Get all dependencies for a task (upstream and downstream)."""
        result = self.graph.query(
            """
            MATCH (t:Task {task_id: $task_id})
            OPTIONAL MATCH (t)-[d:DEPENDS_ON]->(dep:Task)
            OPTIONAL MATCH (downstream:Task)-[d2:DEPENDS_ON]->(t)
            RETURN collect(DISTINCT {task: dep.name, direction: 'depends_on', quote: d.source_quote}) AS prerequisites,
                   collect(DISTINCT {task: downstream.name, direction: 'required_by', quote: d2.source_quote}) AS downstream
            """,
            {'task_id': task_id}
        )
        return result.result_set or []

    def get_compliance_for_task(self, task_id: str) -> list:
        """Get all regulations that apply to a task."""
        result = self.graph.query(
            """
            MATCH (t:Task {task_id: $task_id})-[c:COMPLIES_WITH]->(r:Regulation)
            RETURN r.name AS regulation, r.jurisdiction, r.citation, c.source_quote
            """,
            {'task_id': task_id}
        )
        return result.result_set or []

    def get_incidents_for_playbook(self, playbook_id: str) -> list:
        """Get all incidents that triggered a specific playbook."""
        result = self.graph.query(
            """
            MATCH (i:Incident)-[:TRIGGERS]->(pb:Playbook {playbook_id: $playbook_id})
            RETURN i.incident_id, i.type, i.severity, i.detected_at, i.status
            ORDER BY i.detected_at DESC
            """,
            {'playbook_id': playbook_id}
        )
        return result.result_set or []

    def get_evidence_path_formatted(self, node_ids: list) -> list:
        """Get evidence path and return as formatted string.

        Uses explicit 1-hop query (not variable-length paths) for FalkorDB
        compatibility and predictable performance on large graphs.
        Uses business keys (task_id, entity_id, reg_id, incident_id, process_id)
        instead of internal FalkorDB IDs for portability.
        """
        result = self.graph.query(
            """
            MATCH (n)-[r]-(m)
            WHERE n.task_id IN $node_ids
               OR n.entity_id IN $node_ids
               OR n.reg_id IN $node_ids
               OR n.incident_id IN $node_ids
               OR n.process_id IN $node_ids
            RETURN COALESCE(n.name, n.task_id, n.entity_id, n.reg_id, n.incident_id, n.process_id, 'unknown') AS src,
                   COALESCE(m.name, m.task_id, m.entity_id, m.reg_id, m.incident_id, m.process_id, 'unknown') AS dst,
                   type(r) AS rel_type
            LIMIT 10
            """,
            {'node_ids': node_ids}
        )
        return result.result_set or []

    def get_all_incidents(self) -> list:
        """Get all incidents."""
        result = self.graph.query(
            "MATCH (i:Incident) RETURN i.incident_id, i.type, i.severity, i.status ORDER BY i.detected_at DESC"
        )
        return result.result_set or []

    def get_all_vendors(self) -> list:
        """Get all vendors."""
        result = self.graph.query(
            "MATCH (v:Vendor) RETURN v.entity_id, v.name, v.type, v.risk_score ORDER BY v.name"
        )
        return result.result_set or []

    def get_all_documents(self) -> list:
        """Get all documents."""
        result = self.graph.query(
            "MATCH (d:Document) RETURN d.doc_id, d.title, d.type ORDER BY d.title"
        )
        return result.result_set or []

    def get_all_processes(self) -> list:
        """Get all processes."""
        result = self.graph.query(
            "MATCH (p:Process) RETURN p.process_id, p.name, p.domain ORDER BY p.name"
        )
        return result.result_set or []

    def get_playbook_steps(self, incident_type: str) -> list:
        """Get ordered playbook steps with contacts and deadlines."""
        result = self.graph.query(
            """
            MATCH (pb:Playbook {incident_type: $incident_type})-[hs:HAS_STEP]->(step:StepTemplate)
            OPTIONAL MATCH (step)-[:CONTACT]->(contact:Person)
            RETURN pb.name AS playbook,
                   pb.source_citation AS source,
                   step.name AS action,
                   hs.order AS step_order,
                   hs.amount AS amount,
                   hs.unit AS unit,
                   hs.trigger AS trigger,
                   contact.name AS contact_name,
                   contact.role AS contact_role,
                   hs.legal_citation AS legal_basis
            ORDER BY hs.order
            """,
            {'incident_type': incident_type}
        )
        return result.result_set or []

    def get_tasks_by_feasibility(self, min_feasibility: float = 0.5, limit: int = 20) -> list:
        """Get tasks above a feasibility threshold."""
        result = self.graph.query(
            """
            MATCH (t:Task)
            WHERE t.automation_feasibility >= $min_feasibility
            RETURN t.task_id, t.name, t.automation_feasibility,
                   t.automation_impact, t.hours_per_year
            ORDER BY t.automation_feasibility DESC
            LIMIT $limit
            """,
            {'min_feasibility': min_feasibility, 'limit': limit}
        )
        return result.result_set or []

    def full_text_search_tasks(self, term: str, limit: int = 20) -> list:
        """Full-text search on tasks using RediSearch TF-IDF."""
        result = self.graph.query(
            """
            CALL db.idx.fulltext.queryNodes('Task', $term)
            YIELD node, score
            RETURN node.task_id, node.name, node.description, score
            ORDER BY score DESC
            LIMIT $limit
            """,
            {'term': term, 'limit': limit}
        )
        return result.result_set or []

    def semantic_search_tasks(self, query_vector: list, k: int = 5) -> list:
        """Vector similarity search on tasks using HNSW."""
        result = self.graph.query(
            """
            CALL db.idx.vector.queryNodes('Task', 'embedding', $k, vecf32($query_vector))
            YIELD node, score
            RETURN node.task_id, node.name, node.description, score
            ORDER BY score DESC
            """,
            {'k': k, 'query_vector': query_vector}
        )
        return result.result_set or []

    def get_graph_stats(self) -> dict:
        """Get counts of nodes and relationships."""
        node_counts = {}
        for label in ['Task', 'Person', 'Playbook', 'StepTemplate', 'Process',
                      'Document', 'Regulation', 'Incident', 'Vendor']:
            result = self.graph.query(f"MATCH (n:{label}) RETURN count(n) AS cnt")
            node_counts[label] = result.result_set[0][0] if result.result_set else 0

        rel_result = self.graph.query(
            "MATCH ()-[r]->() RETURN type(r) AS rel_type, count(r) AS cnt"
        )
        rel_counts = {row[0]: row[1] for row in (rel_result.result_set or [])}

        return {'nodes': node_counts, 'relationships': rel_counts}

    def get_all_playbooks(self) -> list:
        """Get all playbooks."""
        result = self.graph.query("MATCH (pb:Playbook) RETURN pb.name, pb.incident_type")
        return result.result_set or []

    def get_all_tasks(self) -> list:
        """Get all tasks."""
        result = self.graph.query(
            "MATCH (t:Task) RETURN t.task_id, t.name ORDER BY t.name"
        )
        return result.result_set or []

    def get_all_regulations(self) -> list:
        """Get all regulations."""
        result = self.graph.query(
            "MATCH (r:Regulation) RETURN r.reg_id, r.name, r.jurisdiction"
        )
        return result.result_set or []

    def get_evidence_path(self, node_ids: list) -> list:
        """Get the evidence subgraph connecting result nodes.

        Uses explicit 1-hop and 2-hop queries (not variable-length paths)
        for FalkorDB compatibility and predictable performance on large graphs.
        Uses business keys (task_id, entity_id, reg_id, incident_id, process_id)
        instead of internal FalkorDB IDs for portability.
        """
        # Hop 1: direct neighbors
        result = self.graph.query(
            """
            MATCH (n)-[r]-(m)
            WHERE n.task_id IN $node_ids
               OR n.entity_id IN $node_ids
               OR n.reg_id IN $node_ids
               OR n.incident_id IN $node_ids
               OR n.process_id IN $node_ids
            RETURN COALESCE(n.name, n.task_id, n.entity_id, n.reg_id, n.incident_id, n.process_id) AS src,
                   COALESCE(m.name, m.task_id, m.entity_id, m.reg_id, m.incident_id, m.process_id) AS dst,
                   type(r) AS rel_type
            LIMIT 20
            """,
            {'node_ids': node_ids}
        )
        return result.result_set or []

    # ========================================================================
    # NEW: Graph-powered methods for the agent (close the demo-graph gap)
    # ========================================================================

    def get_playbook_steps_graph(self, incident_type: str) -> list:
        """Get playbook steps by traversing the graph.

        Traverses: Playbook →HAS_STEP→ StepTemplate →CONTACT→ Person
        Returns structured steps with deadlines, contacts, legal citations.
        This replaces the hardcoded get_playbook() dict.
        """
        result = self.graph.query(
            """
            MATCH (pb:Playbook {incident_type: $incident_type})-[hs:HAS_STEP]->(step:StepTemplate)
            OPTIONAL MATCH (step)-[:CONTACT]->(contact:Person)
            RETURN pb.name AS playbook_name,
                   pb.source_citation AS source,
                   step.step_id AS step_id,
                   step.name AS step_name,
                   hs.order AS step_order,
                   hs.amount AS amount,
                   hs.unit AS unit,
                   hs.trigger AS trigger,
                   contact.name AS contact_name,
                   contact.role AS contact_role,
                   hs.legal_citation AS legal_basis
            ORDER BY hs.order
            """,
            {'incident_type': incident_type}
        )
        return result.result_set or []

    def get_tasks_with_context(self) -> list:
        """Get all tasks with their graph context: compliance, dependencies, process.

        This is the graph-powered replacement for get_demo_tasks().
        Returns tasks with their full relationship context from the graph,
        enabling automation assessment that considers graph structure.
        """
        result = self.graph.query(
            """
            MATCH (t:Task)
            OPTIONAL MATCH (t)-[:COMPLIES_WITH]->(r:Regulation)
            OPTIONAL MATCH (t)-[:DEPENDS_ON]->(d:Task)
            OPTIONAL MATCH (p:Process)-[:HAS_TASK]->(t)
            RETURN t.task_id AS task_id,
                   t.name AS name,
                   t.description AS description,
                   t.frequency_per_year AS frequency_per_year,
                   t.time_per_exec_hours AS time_per_exec_hours,
                   t.labor_rate_dollars AS labor_rate_dollars,
                   t.structuredness AS structuredness,
                   t.data_accessibility AS data_accessibility,
                   t.decision_complexity AS decision_complexity,
                   t.exception_rate AS exception_rate,
                   t.error_cost_dollars AS error_cost_dollars,
                   t.compliance_risk AS compliance_risk,
                   t.implementation_cost_annual AS implementation_cost_annual,
                   collect(DISTINCT r.name) AS regulations,
                   collect(DISTINCT r.jurisdiction) AS regulation_jurisdictions,
                   collect(DISTINCT d.task_id) AS depends_on,
                   p.name AS process_name
            ORDER BY t.name
            """
        )
        return result.result_set or []

    def get_compliance_gaps(self) -> list:
        """Find tasks that should comply with regulations but don't.

        Identifies tasks with high compliance_risk (>0.5) that lack
        COMPLIES_WITH edges — potential compliance gaps.
        This is a uniquely graph-powered insight.
        """
        result = self.graph.query(
            """
            MATCH (t:Task)
            WHERE t.compliance_risk > 0.3
            OPTIONAL MATCH (t)-[:COMPLIES_WITH]->(r:Regulation)
            WITH t, collect(r) AS regs
            WHERE size(regs) = 0
            RETURN t.task_id AS task_id,
                   t.name AS name,
                   t.compliance_risk AS risk,
                   t.description AS description
            ORDER BY t.compliance_risk DESC
            """
        )
        return result.result_set or []

    def get_regulation_impact(self, reg_id: str) -> list:
        """Find all tasks and processes affected by a regulation.

        Traverses: Regulation ←COMPLIES_WITH- Task -HAS_TASK→ Process
        Returns the blast radius of a regulatory change.
        """
        result = self.graph.query(
            """
            MATCH (r:Regulation {reg_id: $reg_id})<-[:COMPLIES_WITH]-(t:Task)
            OPTIONAL MATCH (p:Process)-[:HAS_TASK]->(t)
            OPTIONAL MATCH (t)-[:DEPENDS_ON]->(downstream:Task)
            RETURN t.task_id AS task_id,
                   t.name AS task_name,
                   t.compliance_risk AS compliance_risk,
                   p.name AS process_name,
                   collect(DISTINCT downstream.name) AS downstream_tasks
            ORDER BY t.compliance_risk DESC
            """,
            {'reg_id': reg_id}
        )
        return result.result_set or []

    def get_process_critical_path(self, process_id: str) -> list:
        """Find the critical path through a process using graph traversal.

        Uses DEPENDS_ON edges to find the longest chain of dependent tasks.
        Uses explicit multi-hop BFS (not variable-length paths) for FalkorDB compatibility.
        """
        result = self.graph.query(
            """
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
            RETURN t.task_id AS task_id,
                   t.name AS task_name,
                   t.time_per_exec_hours AS time_hours,
                   depth AS dependency_depth,
                   chain AS dependency_chain
            ORDER BY depth DESC, t.time_per_exec_hours DESC
            """,
            {'process_id': process_id}
        )
        return result.result_set or []

    def get_vendor_risk_propagation(self, vendor_id: str) -> list:
        """Get vendor risk propagated through the graph.

        Combines cascade impact with compliance context:
        Vendor → Process → Task → Regulation
        Shows not just what breaks, but what compliance obligations are at risk.
        """
        result = self.graph.query(
            """
            MATCH (v:Vendor {entity_id: $vendor_id})-[:PROVIDES_SERVICE_FOR]->(target)
            OPTIONAL MATCH (target)-[:HAS_TASK]->(t:Task)
            OPTIONAL MATCH (t)-[:COMPLIES_WITH]->(r:Regulation)
            WITH v, target, t, r,
                 CASE WHEN target:Process THEN 'Process' ELSE 'Task' END AS target_type
            RETURN target.name AS entity_name,
                   target_type,
                   t.name AS task_name,
                   r.name AS regulation,
                   r.jurisdiction AS jurisdiction,
                   t.compliance_risk AS task_risk
            ORDER BY target_type, target.name
            """,
            {'vendor_id': vendor_id}
        )
        return result.result_set or []

    def get_task_embedding(self, task_id: str) -> list:
        """Get the stored embedding vector for a task."""
        result = self.graph.query(
            "MATCH (t:Task {task_id: $task_id}) RETURN t.embedding",
            {'task_id': task_id}
        )
        if result.result_set and result.result_set[0][0]:
            return result.result_set[0][0]
        return None

    def get_similar_tasks_graph(self, task_id: str, k: int = 5) -> list:
        """Find tasks similar to a given task using vector search + graph context.

        Combines HNSW vector similarity with graph structure:
        finds tasks with similar embeddings that also share process/regulation context.
        """
        embedding = self.get_task_embedding(task_id)
        if not embedding:
            return []

        result = self.graph.query(
            """
            CALL db.idx.vector.queryNodes('Task', 'embedding', $k, vecf32($qv))
            YIELD node, score
            WHERE node.task_id <> $exclude_id
            OPTIONAL MATCH (node)-[:COMPLIES_WITH]->(r:Regulation)
            RETURN node.task_id AS task_id,
                   node.name AS name,
                   score,
                   collect(DISTINCT r.name) AS shared_regulations
            ORDER BY score DESC
            """,
            {'k': k, 'qv': embedding, 'exclude_id': task_id}
        )
        return result.result_set or []

    def get_incident_timeline(self, incident_id: str) -> list:
        """Get the full incident timeline from the graph.

        Traverses: Incident →TRIGGERS→ Playbook →HAS_STEP→ StepTemplate →CONTACT→ Person
        Returns the complete response plan for a specific incident.
        """
        result = self.graph.query(
            """
            MATCH (i:Incident {incident_id: $incident_id})-[:TRIGGERS]->(pb:Playbook)
            OPTIONAL MATCH (pb)-[hs:HAS_STEP]->(step:StepTemplate)
            OPTIONAL MATCH (step)-[:CONTACT]->(contact:Person)
            RETURN i.incident_id AS incident_id,
                   i.type AS incident_type,
                   i.severity AS severity,
                   pb.name AS playbook_name,
                   step.name AS step_name,
                   hs.order AS step_order,
                   hs.amount AS amount,
                   hs.unit AS unit,
                   contact.name AS contact_name,
                   contact.role AS contact_role,
                   hs.legal_citation AS legal_basis
            ORDER BY hs.order
            """,
            {'incident_id': incident_id}
        )
        return result.result_set or []


def get_default_db(port: int = 6380) -> CompanyBrainDB:
    """Get a connection to the default FalkorDB instance."""
    return CompanyBrainDB(host='localhost', port=port, graph_name='company_brain')
