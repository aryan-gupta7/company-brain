# Company Brain — Idea & Vision

> **FalkorDB Hackathon 2026 — Track 03: Company Brain**
> *An AI agent that leads your company when you're not there.*
>
> **v3** — Revised after technical review. Scope cut, claims corrected, demo honest.

---

## The Problem I've Seen Firsthand

I've watched companies — real ones, with real people — struggle with the same problems over and over. Not because the problems are hard, but because **nobody has the full picture**. The knowledge is scattered. The processes are undocumented. The dependencies are invisible. And when something goes wrong, people panic because they don't know what to do next.

Here's what I've actually seen:

**The owner who doesn't know their own cash flow.** Money goes out to vendors, comes in from customers, but nobody can tell you in real time: "If Customer A pays late, which suppliers can we still pay?" The CFO has a spreadsheet. The sales team has a CRM. The ops team has invoices. Nobody has the graph.

**The project that silently dies.** A critical task gets missed. Nobody notices for two weeks. Then the whole project is delayed, and everyone asks "how did this happen?" The answer: the dependency chain was in someone's head, and that person was on vacation.

**The intern who sits idle for a week.** New hire starts. Nobody tells them what to do, what to read, who to talk to, what systems to access. They "figure it out." Two weeks of productivity lost. Multiply by every hire, every year.

**The breach where nobody knows the playbook.** Something goes wrong — cyber attack, theft, data leak. People scramble. Who do we call? What are the legal deadlines? What needs to be filed, and when? The incident response plan is a PDF on SharePoint that nobody has read.

**The compliance that small companies skip.** Not because they're lazy, but because it's too complex and too expensive to hire a compliance officer. Then an employee leaves, sues, and the company realizes they missed a step in offboarding that would have protected them.

**The automation that nobody plans.** Companies throw RPA at random tasks. Some work, some don't. Nobody has assessed: what CAN be automated, what SHOULD be automated, and what MUST stay human. They're guessing.

---

## What "Company Brain" Means

Company Brain is a **single AI agent** that understands, monitors, and acts on behalf of a company's operations. It's backed by a **Process Knowledge Graph** — a graph database that models how the company actually works: its tasks, dependencies, people, documents, and obligations.

The agent specializes based on what you ask it:
- **"We had a breach"** → It traverses the incident response graph, computes deadlines, identifies contacts, and generates a response plan with legal citations.
- **"What can we automate?"** → It analyzes your processes, scores them on feasibility × impact, and tells you what to automate now, what to redesign first, and what to keep human.
- **"What's our exposure?"** → It traces the graph across departments — vendor → contract → service — and shows you the blast radius.

**The graph is the brain. The agent is the interface. The evidence is the proof.**

---

## The Vision

**A company that doesn't fall apart when the leaders step away.**

Not fully autonomous — that's science fiction and dangerous. But:

- When a server gets breached, the agent knows the playbook. It notifies the right people, starts the clock on regulatory deadlines, and drafts the incident report — with every deadline computed deterministically and every citation linked to source text.
- When a critical task is missed, the agent detects the broken chain, traces the downstream impact through the dependency graph, and alerts the people who can fix it — showing the exact path of the break.
- When the owner asks "What happens to our projects if Vendor X goes down?", the agent traces the vendor → service → project graph and returns a cascade analysis with evidence.
- When the owner asks "What can we actually automate?", the agent presents a feasibility × impact analysis with honest math — every input labeled as user-provided, estimated, or default.

**The company's institutional knowledge, captured and actionable.**

---

## What Makes This Different

**Not document RAG.** Every "company AI" today does document search: upload docs, ask questions, get answers. That's a search engine. Company Brain models **processes** — what the company DOES, not just what its documents SAY.

**Not a chatbot with a graph.** The graph isn't decoration. It's the reasoning engine. Every answer comes with an evidence subgraph — the actual path through the graph that produced the conclusion. You can see *why* the agent said what it said.

**Not fake intelligence.** We're honest about what we can extract from documents and what needs human input. We show our evidence. We cite our sources. We flag uncertainty. We label synthetic demo data as synthetic. We say "decision support, not legal advice."

**Not hardcoded rules.** The system learns YOUR company's processes. It doesn't assume every company works the same way.

---

## Target Outcomes

### For the Demo (3 modules, honest scope)

**Module 1: Incident Response** (STRONGEST — lead with this)
> "We detected unauthorized access to our production database at 2:30 PM UTC."

The agent traverses the curated playbook graph, computes deterministic deadlines (GDPR 72 hours from awareness = Thursday 14:30 UTC), identifies contacts, and generates a complete response plan — with legal citations, evidence subgraphs, and similar incidents from real SEC filings.

**Module 2: Process Extraction + Dependency Graph**
> "Here's our onboarding SOP. What did you extract?"

The agent ingests a real document, extracts tasks and dependencies with confidence scores, builds the dependency graph, detects cycles, and presents it for user review. Every edge carries a verbatim source quote. Honest about what it got right and what it's unsure about.

**Module 3: Automation Assessment**
> "Analyze our processes. What can we automate?"

The agent scores extracted tasks on feasibility × impact using honest math (frequency × duration in hours/year, gates for risk, human-in-loop for high-stakes). Returns quadrant classification with full derivation — every input labeled with its source.

### What We Cut (And Why)

| Cut Feature | Reason |
|---|---|
| Cash flow optimization | Doesn't need a graph (pandas arithmetic). Distracts from core story. |
| Full compliance graph (87 obligations) | Too broad for 3 days. Narrowed to breach notification only. |
| 6 separate agents + router | Unnecessary complexity. One agent with scoped tools is cheaper and more reliable. |
| Live ingestion of 25K docs | Not realistic for demo. Pre-baked data + one live extraction demo. |
| Financial investigation agent | Overlaps with cascade feature. Cut to reduce scope. |

---

## Who This Is For

**Small and medium businesses** that:
- Don't have a dedicated compliance officer
- Don't have a PMO tracking every dependency
- Don't have an incident response playbook (or have one nobody reads)
- Lose productivity to onboarding chaos
- Make decisions without seeing the full picture
- Run on institutional knowledge that walks out the door when people leave

**The owner who wants to step away** — go on vacation, take a sabbatical, focus on strategy — without the operation falling apart.

### The Input Assumption Problem (Honest)

Our system needs process data as input. But our target user — a 15-person company — often doesn't have documented SOPs. **This is a real tension.**

How we address it:
1. **Companies WITH documentation**: Upload SOPs → extract process graph → agent traverses it.
2. **Companies WITHOUT documentation**: The agent conducts an **interview/elicitation flow** — asks structured questions, builds the graph from answers. This is the real product for SMBs: not "upload your docs" but "tell me how you work and I'll map it."
3. **Curated playbooks**: Incident response doesn't depend on extraction — it's curated from NIST/ISO standards. Works even for companies with zero documentation.

---

## What Success Looks Like

A judge watches the demo and thinks: *"I need this for my company."*

Not "that's clever." Not "interesting tech." **"I need this."**

Because every single feature solves a problem they've actually had:
- "Who do I call RIGHT NOW?" → Incident response with contacts and deadlines
- "What breaks if this is late?" → Dependency cascade with evidence path
- "What can I actually automate?" → Feasibility × impact with honest math
- "Are we compliant?" → Breach notification obligations with citations
- "How do we onboard this person?" → Curated role-task templates

If a judge doesn't recognize at least one of these problems from their own experience, we've built the wrong thing.

---

## Non-Goals

What we are NOT building:
- A generic chatbot for documents
- A replacement for human judgment on strategic decisions
- A system that claims to extract perfect process data from messy documents without human review
- Legal advice (we provide decision support with cited sources)
- Financial advice (cash flow projections are estimates, not planning)
- Full autonomous operation (humans stay in the loop for high-stakes actions)
- A system that works without any human input on operational data
- A system that hides its uncertainty (we show confidence scores and evidence)

---

## Technical Honesty (What We Verified)

After a thorough technical review, every claim in this document has been verified:

| Claim | Status |
|---|---|
| FalkorDB v6.0.2 (Rust) / v4.x | ✅ Verified — GitHub releases |
| Vector search: `db.idx.vector.queryNodes()` | ✅ Verified — correct syntax (NOT `embedding_similarity()`) |
| Full-text: `db.idx.fulltext.queryNodes()` with TF-IDF | ✅ Verified — RediSearch, NOT BM25 |
| GDPR Art. 33: 72 hours from awareness | ✅ Verified — primary source |
| CCPA: 30 calendar days from discovery (SB 446) | ⚠️ Verify enactment status before demo |
| HIPAA: 60 days from discovery + nuances | ✅ Verified — 45 CFR §164.404/408 |
| SEC Item 1.05 | ❌ Removed — applies to public companies only, irrelevant to SMBs |
| Graph algorithms (PageRank, betweenness) | ❌ Not verified in FalkorDB docs — using networkx instead |
| GraphRAG SDK accuracy on SOPs | ⚠️ Not yet measured — must test on 5-10 real SOPs before demo |

---

## The Core Thesis

**Companies don't fail because of bad strategy. They fail because of broken processes, missed dependencies, and invisible risks.**

Company Brain makes the invisible visible. It connects the dots that nobody has time to connect. And it acts on what it finds — not autonomously, but as a force multiplier for the humans who run the company.

The graph is the brain. The agent is the interface. The evidence is the proof.
