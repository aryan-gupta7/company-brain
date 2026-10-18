# Hackathon Submission Form — Copy-Paste Ready

## Project Title
Company Brain

## Track
Track 03: Company Brain

## Description
An AI agent that understands how your company works — backed by a FalkorDB Process Knowledge Graph that connects people, processes, tasks, documents, vendors, and compliance obligations. Ask it "We had a breach" and it traverses the incident response graph, computes deterministic deadlines, identifies contacts, and finds similar incidents from real SEC filings. Ask "What can we automate?" and it scores your processes on feasibility × impact with honest math. Ask "What breaks if Vendor X goes down?" and it traces the blast radius through the dependency graph.

## Problem + Audience
Companies don't fail because of bad strategy. They fail because of broken processes, missed dependencies, and invisible risks. Company Brain makes the invisible visible.

Built for small and medium businesses that don't have a dedicated compliance officer, PMO, or incident response playbook. The owner who wants to step away without the operation falling apart. The team that makes decisions without seeing the full picture.

The graph is the brain. The agent is the interface. The evidence is the proof.

## How You Used FalkorDB
FalkorDB is the unified knowledge layer — not a bolt-on. We use all four index types in one engine:

1. GRAPH (GraphBLAS sparse matrices): Process Knowledge Graph with 9 node types and 8 relationship types. Multi-hop traversals for incident response playbook steps, cascade analysis (3-hop BFS), vendor risk propagation, and compliance gap detection.

2. VECTOR (HNSW, 384-dim cosine): Semantic search for similar incidents against 100 real SEC 8-K Item 1.05 breach disclosures. Similar task matching combining embedding similarity with shared regulation context.

3. FULL-TEXT (RediSearch TF-IDF): Keyword search across tasks, documents, playbooks, and regulations.

4. RANGE: Property filtering on due dates, automation feasibility, incident severity, vendor risk scores, and regulation effective dates.

We expose the graph through a read-only MCP server with 8 whitelisted Cypher templates — no free-form Cypher, no write operations, parameterized queries only. Every agent answer comes with an evidence subgraph showing the exact path through the graph that produced the conclusion.

## Live Demo / Deployment
Local deployment via Docker + uv:

1. docker run -d --name falkordb-hackathon -p 6380:6379 -p 3001:3000 falkordb/falkordb:latest
2. git clone https://github.com/aryan-gupta7/company-brain.git
3. cd company-brain && uv sync
4. bash run.sh

This auto-starts FalkorDB, seeds the graph (~137 nodes, 34+ relationships), generates embeddings, fetches 100 real SEC filings, runs 78 tests, and executes all 6 demo modules. Web frontend at http://localhost:8000, FalkorDB GUI at http://localhost:3001.

## AI Disclosure
This project was built with assistance from Claude Code (Anthropic's AI coding assistant). All code was reviewed, tested, and understood by the participant. The graph model, queries, architecture, and technical decisions were designed and verified by the participant.
