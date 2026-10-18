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
