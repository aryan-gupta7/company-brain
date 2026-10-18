"""FastAPI web server for Company Brain.

Serves the frontend and provides REST API endpoints for the agent,
graph queries, search, and cascade analysis.

Usage:
    uv run python -m web.server
"""

import sys; sys.path.insert(0, 'src')

import os
import json
from typing import Optional
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from core.falkordb_client import CompanyBrainDB
from core.deadline_calculator import compute_deadline
from core.automation_scoring import assess, TaskAttributes
from core.embeddings import embed_text
from core.llm_client import llm
from core.sop_parser import parse_sop_document
from core.graph_utils import validate_process_graph
from agent.agent import classify_intent, CompanyBrainAgent
from demo.seed_data import get_playbook


app = FastAPI(title="Company Brain", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Global DB connection ---
db: Optional[CompanyBrainDB] = None
agent: Optional[CompanyBrainAgent] = None


@app.on_event("startup")
def startup():
    global db, agent
    port = int(os.environ.get("FALKORDB_PORT", 6380))
    try:
        db = CompanyBrainDB(port=port)
        db.query("RETURN 1 AS test")
        print(f"  ✅ Connected to FalkorDB on port {port}")
    except Exception as e:
        print(f"  ⚠️  FalkorDB not available: {e}")
        db = None

    playbook_data = {
        'data_breach': get_playbook('data_breach'),
        'ransomware': get_playbook('ransomware'),
    }
    agent = CompanyBrainAgent(playbook_data=playbook_data)
    if db:
        agent.db = db


# --- Request/Response models ---

class QueryRequest(BaseModel):
    query: str


class SearchRequest(BaseModel):
    term: str
    limit: int = 10


class SimilarRequest(BaseModel):
    text: str
    k: int = 5


# --- API Endpoints ---

@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "falkordb": db is not None and db.query("RETURN 1") is not None,
        "llm": llm.available,
        "model": llm.model if llm.available else None,
    }


@app.post("/api/query")
def api_query(req: QueryRequest):
    """Process a natural language query through the agent."""
    if not agent:
        raise HTTPException(503, "Agent not initialized")

    response = agent.handle(req.query)
    return response


@app.get("/api/stats")
def api_stats():
    """Get graph statistics."""
    if not db:
        raise HTTPException(503, "FalkorDB not connected")
    return db.get_graph_stats()


@app.get("/api/graph")
def api_graph():
    """Get full graph data for visualization."""
    if not db:
        raise HTTPException(503, "FalkorDB not connected")

    # Get all nodes with their labels and key properties
    nodes_query = """
    MATCH (n)
    RETURN labels(n)[0] as label, n.name as name, n.reg_id as reg_id,
           n.task_id as task_id, n.incident_id as incident_id,
           n.entity_id as entity_id, n.person_id as person_id,
           n.process_id as process_id, n.doc_id as doc_id,
           n.playbook_id as playbook_id, n.step_id as step_id,
           id(n) as node_id
    LIMIT 200
    """
    nodes_result = db.query(nodes_query) or []

    # Get all relationships
    rels_query = """
    MATCH (a)-[r]->(b)
    RETURN id(a) as source, id(b) as target, type(r) as rel_type
    LIMIT 500
    """
    rels_result = db.query(rels_query) or []

    nodes = []
    seen_ids = set()
    for row in nodes_result:
        node_id = row[10]
        if node_id in seen_ids:
            continue
        seen_ids.add(node_id)
        name = row[1] or row[2] or row[3] or row[4] or row[5] or row[6] or row[7] or row[8] or row[9] or row[10] or f"node_{node_id}"
        nodes.append({
            "id": node_id,
            "label": name[:30],
            "group": row[0],
            "full_label": row[0],
        })

    edges = []
    for row in rels_result:
        edges.append({
            "from": row[0],
            "to": row[1],
            "label": row[2],
        })

    return {"nodes": nodes, "edges": edges}


@app.get("/api/regulations")
def api_regulations():
    """Get all regulations."""
    if not db:
        raise HTTPException(503, "FalkorDB not connected")
    result = db.query("MATCH (r:Regulation) RETURN r.reg_id, r.name, r.jurisdiction, r.citation, r.effective_date, r.status ORDER BY r.name")
    regs = []
    for row in (result or []):
        regs.append({
            "reg_id": row[0],
            "name": row[1],
            "jurisdiction": row[2],
            "citation": row[3],
            "effective_date": row[4],
            "status": row[5] if len(row) > 5 else None,
        })
    return regs


@app.get("/api/vendors")
def api_vendors():
    """Get all vendors."""
    if not db:
        raise HTTPException(503, "FalkorDB not connected")
    result = db.query("MATCH (v:Vendor) RETURN v.entity_id, v.name, v.type, v.risk_score, v.status")
    vendors = []
    for row in (result or []):
        vendors.append({
            "entity_id": row[0],
            "name": row[1],
            "type": row[2],
            "risk_score": row[3],
            "status": row[4],
        })
    return vendors


@app.get("/api/cascade/{vendor_id}")
def api_cascade(vendor_id: str):
    """Get cascade impact for a vendor."""
    if not db:
        raise HTTPException(503, "FalkorDB not connected")
    impact = db.get_cascade_impact(vendor_id)
    return [
        {"entity_id": row[0], "name": row[1], "impact_type": row[2]}
        for row in impact
    ]


@app.post("/api/search")
def api_search(req: SearchRequest):
    """Full-text search."""
    if not db:
        raise HTTPException(503, "FalkorDB not connected")
    results = db.full_text_search_tasks(req.term) or []
    return [
        {"task_id": r[0], "name": r[1], "description": r[2], "score": r[3]}
        for r in results
    ]


@app.post("/api/extract")
def api_extract(req: dict):
    """Parse an SOP document and extract tasks + dependencies."""
    sop_text = req.get('sop_text', '')
    if not sop_text:
        raise HTTPException(400, "Missing 'sop_text' field")

    tasks, deps = parse_sop_document(sop_text)
    validation = validate_process_graph(tasks, deps)

    return {
        "tasks": tasks,
        "dependencies": deps,
        "validation": {
            "valid": validation.get('valid', True),
            "critical_path": validation.get('critical_path', []),
            "path_length_hours": validation.get('path_length_hours', 0),
            "cycles": validation.get('cycles', []),
        },
    }


@app.get("/api/playbook/{incident_type}")
def api_playbook(incident_type: str):
    """Get playbook steps from the graph."""
    if not db:
        raise HTTPException(503, "FalkorDB not connected")
    steps = db.get_playbook_steps_graph(incident_type)
    if not steps:
        raise HTTPException(404, f"No playbook found for '{incident_type}'")

    result = []
    for row in steps:
        _, _, step_id, step_name, order, amount, unit, trigger, contact_name, contact_role, legal_basis = row
        result.append({
            "step_id": step_id,
            "name": step_name,
            "order": order,
            "amount": amount,
            "unit": unit,
            "trigger": trigger,
            "contact": contact_name or "TBD",
            "contact_role": contact_role or "TBD",
            "legal_basis": legal_basis or "",
        })
    return result


@app.post("/api/similar")
def api_similar(req: SimilarRequest):
    """Vector similarity search."""
    if not db:
        raise HTTPException(503, "FalkorDB not connected")
    query_vec = embed_text(req.text)
    result = db.graph.query(
        'CALL db.idx.vector.queryNodes($label, $attr, $k, vecf32($qv)) YIELD node, score RETURN node.incident_id, node.company_name, node.type, node.severity, score ORDER BY score DESC LIMIT $k',
        {'label': 'Incident', 'attr': 'embedding', 'k': req.k, 'qv': query_vec}
    )
    return [
        {"incident_id": r[0], "company_name": r[1], "type": r[2], "severity": r[3], "score": float(r[4])}
        for r in (result.result_set or [])
    ]


# --- Serve frontend ---

@app.get("/")
def root():
    return FileResponse(os.path.join(os.path.dirname(__file__), "static/index.html"))


# Mount static files
static_dir = os.path.join(os.path.dirname(__file__), "static")
app.mount("/static", StaticFiles(directory=static_dir), name="static")


# --- Entry point ---

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("WEB_PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
