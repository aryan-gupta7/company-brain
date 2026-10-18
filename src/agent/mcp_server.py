"""MCP Server for Company Brain — read-only, parameterized tools.

Security model:
- No free-form Cypher. Only pre-validated templates with bound parameters.
- No write operations (no CREATE, SET, DELETE, MERGE exposed).
- No delete_graph.
- All Cypher goes through GRAPH.RO_QUERY (read-only graph query).
"""

from typing import Any, Dict, List, Optional
import json

# --- Pre-validated Cypher templates ---
# Each template is a parameterized Cypher query with $param placeholders.
# The server binds parameters before execution. User/agent Cypher is NEVER accepted.

CYPHER_TEMPLATES = {
    "get_playbook_steps": """
        MATCH (pb:Playbook {incident_type: $incident_type})-[hs:HAS_STEP]->(step:StepTemplate)
        OPTIONAL MATCH (step)-[:CONTACT]->(contact:Person)
        RETURN pb.name AS playbook, pb.source_citation AS source,
               step.name AS action, hs.order AS step_order,
               hs.amount AS amount, hs.unit AS unit,
               hs.trigger AS trigger, contact.name AS contact_name,
               contact.role AS contact_role, hs.legal_citation AS legal_basis
        ORDER BY hs.order
    """,

    "get_entity_connections": """
        MATCH (e {entity_id: $entity_id})-[*1..3]-(connected)
        RETURN DISTINCT labels(connected) AS entity_type,
               connected.name AS name, connected.status AS status
        LIMIT 50
    """,

    "get_process_tasks": """
        MATCH (p:Process {process_id: $process_id})-[:HAS_TASK]->(t:Task)
        OPTIONAL MATCH (t)-[:DEPENDS_ON]->(d:Task)
        RETURN t.task_id, t.name, t.description, t.status,
               collect(d.task_id) AS depends_on
    """,

    "get_compliance_requirements": """
        MATCH (r:Regulation {reg_id: $reg_id})-[:REQUIRES]->(req:Task)
        RETURN r.name AS regulation, req.name AS requirement,
               r.citation AS legal_citation
    """,

    "get_similar_incidents": """
        CALL db.idx.vector.queryNodes('Incident', 'embedding', $k, vecf32($query_vector))
        YIELD node, score
        RETURN node.incident_id, node.type, node.severity,
               node.detected_at, score
        ORDER BY score DESC
        LIMIT $k
    """,

    "get_tasks_by_feasibility": """
        MATCH (t:Task)
        WHERE t.automation_feasibility >= $min_feasibility
        RETURN t.task_id, t.name, t.automation_feasibility,
               t.automation_impact, t.hours_per_year
        ORDER BY t.automation_feasibility DESC
        LIMIT $limit
    """,

    "search_tasks_fulltext": """
        CALL db.idx.fulltext.queryNodes('Task', $term)
        YIELD node, score
        RETURN node.task_id, node.name, node.description, score
        ORDER BY score DESC
        LIMIT $limit
    """,

    "get_evidence_path": """
        MATCH p=(n)-[*1..3]-(m)
        WHERE id(n) IN $node_ids
        RETURN p
        LIMIT 20
    """,
}


def validate_template(template_name: str) -> bool:
    """Check if a template name is in the whitelist."""
    return template_name in CYPHER_TEMPLATES


def get_template(template_name: str) -> str:
    """Get a pre-validated Cypher template."""
    if not validate_template(template_name):
        raise ValueError(
            f"Unknown template: {template_name!r}. "
            f"Available: {list(CYPHER_TEMPLATES.keys())}"
        )
    return CYPHER_TEMPLATES[template_name]


# --- MCP Tool Definitions ---
# These would be exposed via the MCP protocol. For the hackathon,
# we define them as Python functions that the agent calls directly.

TOOL_DEFINITIONS = [
    {
        "name": "query_graph",
        "description": "Execute a pre-validated Cypher template with bound parameters. "
                       "No free-form Cypher accepted.",
        "parameters": {
            "template_name": {"type": "string", "description": "Name of the pre-validated template"},
            "params": {"type": "object", "description": "Key-value parameters for the template"},
        },
    },
    {
        "name": "semantic_search",
        "description": "Vector similarity search: db.idx.vector.queryNodes()",
        "parameters": {
            "label": {"type": "string", "description": "Node label to search (Task, Incident, Document)"},
            "query_vector": {"type": "array", "description": "384-dim embedding vector"},
            "k": {"type": "integer", "description": "Number of results", "default": 10},
        },
    },
    {
        "name": "full_text_search",
        "description": "Full-text search: db.idx.fulltext.queryNodes() (RediSearch TF-IDF)",
        "parameters": {
            "label": {"type": "string", "description": "Node label to search"},
            "term": {"type": "string", "description": "Search term"},
            "limit": {"type": "integer", "description": "Max results", "default": 20},
        },
    },
    {
        "name": "get_evidence_path",
        "description": "Get the evidence subgraph connecting result nodes (explainability).",
        "parameters": {
            "node_ids": {"type": "array", "description": "Internal node IDs to connect"},
        },
    },
    {
        "name": "get_entity_impact",
        "description": "Get all entities within N hops of a source entity (blast radius).",
        "parameters": {
            "entity_id": {"type": "string", "description": "Business key of the entity"},
            "depth": {"type": "integer", "description": "Hop depth (1-5)", "default": 3},
        },
    },
    {
        "name": "compute_automation",
        "description": "Compute automation feasibility × impact for a task. Pure Python.",
        "parameters": {
            "task_attributes": {"type": "object", "description": "Task attributes for scoring"},
        },
    },
]


class MCPServer:
    """Read-only MCP server for Company Brain.

    In production, this wraps the FalkorDB Python client.
    For the hackathon, it can run with a mock FalkorDB backend.
    """

    def __init__(self, falkordb_client=None, graph_name: str = "company_brain"):
        self.client = falkordb_client
        self.graph_name = graph_name

    def execute_template(self, template_name: str, params: dict) -> List[dict]:
        """Execute a pre-validated Cypher template with bound parameters.

        Security: Only whitelisted templates. No free-form Cypher.
        """
        if not validate_template(template_name):
            raise ValueError(f"Template not whitelisted: {template_name!r}")

        Cypher = get_template(template_name)

        if self.client is None:
            # Mock mode for testing without FalkorDB
            return self._mock_execute(template_name, params)

        # Real execution via FalkorDB client (read-only)
        graph = self.client.select_graph(self.graph_name)
        # Use ro_query for read-only enforcement
        result = graph.ro_query(cypher, params)
        return result.result_set

    def _mock_execute(self, template_name: str, params: dict) -> List[dict]:
        """Mock execution for testing without a live FalkorDB."""
        return [{"template": template_name, "params": params, "mock": True}]

    def list_tools(self) -> List[dict]:
        """Return available tool definitions."""
        return TOOL_DEFINITIONS

    def get_available_templates(self) -> List[str]:
        """Return list of whitelisted template names."""
        return list(CYPHER_TEMPLATES.keys())
