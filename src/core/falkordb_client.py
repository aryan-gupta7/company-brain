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
                    t.compliance_risk = $compliance_risk
                """,
                task
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
                    r.effective_date = $effective_date
                """,
                reg
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
        """Get evidence path and return as formatted string."""
        result = self.graph.query(
            """
            MATCH p=(n)-[*1..3]-(m)
            WHERE id(n) IN $node_ids
            RETURN [node IN nodes(p) | COALESCE(node.name, node.task_id, node.incident_id, 'unknown')] AS path_nodes,
                   [rel IN relationships(p) | type(rel)] AS path_rels
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
        """Get the evidence subgraph connecting result nodes."""
        result = self.graph.query(
            """
            MATCH p=(n)-[*1..3]-(m)
            WHERE id(n) IN $node_ids
            RETURN p
            LIMIT 20
            """,
            {'node_ids': node_ids}
        )
        return result.result_set or []


def get_default_db(port: int = 6380) -> CompanyBrainDB:
    """Get a connection to the default FalkorDB instance."""
    return CompanyBrainDB(host='localhost', port=port, graph_name='company_brain')
