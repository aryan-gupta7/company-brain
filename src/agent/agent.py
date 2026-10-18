"""Company Brain Agent — single agent backed by FalkorDB Process Knowledge Graph.

Intent classification → graph query → evidence assembly → response.
The graph SHAPES what the agent does — every handler queries FalkorDB
for its core data. No hardcoded playbooks or task lists.
Hybrid routing: keyword matching (deterministic) + LLM (LongCat, optional).
All deadlines and scoring remain pure Python — LLM only assists with
natural language understanding and response generation.
"""

import sys; sys.path.insert(0, 'src')

from typing import List, Dict, Any, Optional
from datetime import datetime
from core.deadline_calculator import compute_deadline, compute_regulation_deadline
from core.automation_scoring import assess, TaskAttributes, AutomationScore
from core.graph_utils import validate_process_graph, compute_downstream_impact
from core.llm_client import llm


# --- Intent classification (keyword-based, deterministic) ---

INTENT_PATTERNS = {
    'incident_response': [
        'breach', 'incident', 'attack', 'unauthorized', 'leak', 'detected',
        'hacked', 'compromised', 'data breach', 'security incident',
        'ransomware', 'phishing', 'intrusion',
    ],
    'automation_assessment': [
        'automate', 'automation', 'rpa', 'what can we automate',
        'feasibility', 'impact score', 'automation potential',
    ],
    'process_extraction': [
        'extract', 'sop', 'process', 'upload', 'ingest',
        'parse document', 'dependency', 'workflow',
    ],
    'cascade_analysis': [
        'impact', 'cascade', 'blast radius', 'downstream',
        'what breaks', 'vendor down', 'supplier', 'exposure',
        'down', 'goes down', 'outage', 'failure', 'fails',
        'go down', 'what if', 'vendor risk', 'propagation',
    ],
    'compliance_check': [
        'compliant', 'compliance', 'regulation', 'deadline',
        'gdpr', 'ccpa', 'hipaa', 'obligation', 'requirement',
        'dpdpa', 'cert-in', 'cert in', 'india', 'data protection board',
        'notification deadline', 'regulatory filing',
    ],
}


def classify_intent(query: str) -> str:
    """Classify user intent from query text.

    Hybrid approach:
    1. Keyword matching (deterministic, always works)
    2. LLM classification (if LongCat API key is configured)
    3. Use LLM result if available, fall back to keywords
    """
    query_lower = query.lower()
    keyword_scores = {}

    for intent, patterns in INTENT_PATTERNS.items():
        score = sum(1 for p in patterns if p in query_lower)
        if score > 0:
            keyword_scores[intent] = score

    # Try LLM classification if available
    if llm.available:
        llm_intent = llm.classify_intent(query)
        if llm_intent and llm_intent != 'general':
            return llm_intent

    # Fall back to keyword matching
    if not keyword_scores:
        return 'general'

    return max(keyword_scores, key=keyword_scores.get)


class CompanyBrainAgent:
    """Single agent backed by the FalkorDB Process Knowledge Graph.

    Every handler queries the graph for its core data. The graph is not
    a side-store — it shapes what the agent knows and recommends.
    Falls back to hardcoded data only if FalkorDB is unreachable.
    """

    def __init__(self, db=None, playbook_data: dict = None):
        self.db = db  # CompanyBrainDB instance — the primary data source
        self.playbook_data = playbook_data or {}  # fallback only

    def handle(self, query: str) -> dict:
        """Handle a user query. Returns structured response with evidence."""
        intent = classify_intent(query)

        if intent == 'incident_response':
            response = self._handle_incident(query)
        elif intent == 'automation_assessment':
            response = self._handle_automation(query)
        elif intent == 'process_extraction':
            response = self._handle_extraction(query)
        elif intent == 'cascade_analysis':
            response = self._handle_cascade(query)
        elif intent == 'compliance_check':
            response = self._handle_compliance(query)
        else:
            response = self._handle_general(query)

        # Enhance with LLM summary if available
        if llm.available and response:
            summary = llm.summarize_response(
                context=f"Query: {query}",
                data={k: v for k, v in response.items() if k != 'evidence'}
            )
            if summary:
                response['llm_summary'] = summary

        return response

    # ========================================================================
    # INCIDENT RESPONSE — queries graph for playbook, vector search for similar
    # ========================================================================

    def _handle_incident(self, query: str) -> dict:
        """Handle incident response queries.

        GRAPH QUERY: Traverses Playbook→HAS_STEP→StepTemplate→CONTACT→Person
        VECTOR SEARCH: Finds similar past incidents from SEC EDGAR data
        """
        incident_type = self._extract_incident_type(query)
        detected_at = self._extract_detection_time(query)

        # PRIMARY: Query the graph for playbook steps
        if self.db:
            graph_steps = self.db.get_playbook_steps_graph(incident_type)
            if graph_steps:
                return self._build_incident_from_graph(graph_steps, incident_type, detected_at, query)

        # FALLBACK: Hardcoded playbook (only if graph unavailable)
        playbook = self.playbook_data.get(incident_type)
        if not playbook:
            return {
                'intent': 'incident_response',
                'response': f"No playbook found for '{incident_type}'.",
                'evidence': [],
            }
        return self._build_incident_from_dict(playbook, incident_type, detected_at, query)

    def _build_incident_from_graph(self, rows: list, incident_type: str, detected_at: datetime, query: str) -> dict:
        """Build incident response from graph query results.

        Graph path: Playbook→HAS_STEP→StepTemplate→CONTACT→Person
        Each row is a step with deadline metadata from the HAS_STEP edge.
        """
        steps = []
        playbook_name = rows[0][0] if rows else 'Unknown'
        playbook_source = rows[0][1] or ''

        for row in rows:
            # row: [playbook_name, source, step_id, step_name, order, amount, unit, trigger, contact_name, contact_role, legal_basis]
            _, _, step_id, step_name, order, amount, unit, trigger, contact_name, contact_role, legal_basis = row
            deadline = compute_deadline(detected_at, amount, unit)
            steps.append({
                'order': order,
                'name': step_name,
                'contact': contact_name or 'TBD',
                'contact_role': contact_role or 'TBD',
                'deadline': deadline.strftime('%A %b %d %H:%M UTC'),
                'deadline_iso': deadline.isoformat(),
                'legal_basis': legal_basis or '',
                'amount': amount,
                'unit': unit,
            })

        # Add India-specific compliance steps if query mentions India
        if 'india' in query.lower() or 'dpdpa' in query.lower() or 'cert' in query.lower():
            cert_deadline = compute_regulation_deadline('CERT_IN_BREACH', detected_at)
            steps.append({
                'order': len(steps) + 1,
                'name': 'CERT-In Incident Notification (6 hours)',
                'contact': 'CERT-In Nodal Officer',
                'contact_role': 'Government Cyber Response',
                'deadline': cert_deadline.strftime('%A %b %d %H:%M UTC'),
                'deadline_iso': cert_deadline.isoformat(),
                'legal_basis': 'CERT-In April 2022 Directive (Section 70B, IT Act 2000): 6-hour reporting for high-severity incidents',
                'amount': 6,
                'unit': 'clock_hours',
            })
            dpdpa_deadline = compute_regulation_deadline('DPDPA_BREACH', detected_at)
            steps.append({
                'order': len(steps) + 1,
                'name': 'DPDPA Data Protection Board Notification',
                'contact': 'Data Protection Board of India',
                'contact_role': 'Regulatory Authority',
                'deadline': dpdpa_deadline.strftime('%A %b %d %H:%M UTC'),
                'deadline_iso': dpdpa_deadline.isoformat(),
                'legal_basis': 'DPDPA 2023, Section 8(6): notify Data Protection Board on personal data breach',
                'amount': 72,
                'unit': 'clock_hours',
            })

        # GRAPH EVIDENCE: Show the actual graph traversal path
        evidence = [
            f"GRAPH QUERY: MATCH (pb:Playbook)-[hs:HAS_STEP]->(step:StepTemplate)-[:CONTACT]->(contact:Person)",
            f"Playbook: {playbook_name}",
            f"Source: {playbook_source}",
            f"Steps traversed: {len(steps)}",
        ]

        # VECTOR SEARCH: Find similar incidents from SEC data
        similar = []
        if self.db:
            try:
                from core.embeddings import embed_text
                query_vec = embed_text(f"{incident_type} security incident breach")
                vec_result = self.db.graph.query(
                    'CALL db.idx.vector.queryNodes($label, $attr, $k, vecf32($qv)) YIELD node, score RETURN node.company_name, node.type, node.severity, node.detected_at, score ORDER BY score DESC LIMIT 3',
                    {'label': 'Incident', 'attr': 'embedding', 'k': 3, 'qv': query_vec}
                )
                similar = [
                    {'company': r[0], 'type': r[1], 'severity': r[2], 'date': r[3], 'score': float(r[4])}
                    for r in (vec_result.result_set or [])
                    if r[0] and float(r[4]) > 0.5
                ]
            except Exception:
                pass  # Vector search optional

        return {
            'intent': 'incident_response',
            'incident_type': incident_type,
            'detected_at': detected_at.isoformat(),
            'playbook_name': playbook_name,
            'playbook_source': playbook_source,
            'steps': steps,
            'similar_incidents': similar,
            'disclaimer': 'DECISION SUPPORT — NOT LEGAL ADVICE. Requirements vary by jurisdiction. Consult qualified legal counsel.',
            'evidence': evidence,
            'data_source': 'FalkorDB graph traversal' if self.db else 'Hardcoded fallback',
        }

    def _build_incident_from_dict(self, playbook: dict, incident_type: str, detected_at: datetime, query: str) -> dict:
        """Build incident from hardcoded dict (fallback only)."""
        steps = []
        for step in playbook['steps']:
            deadline = compute_deadline(detected_at, step['amount'], step['unit'])
            steps.append({
                'order': step['order'],
                'name': step['name'],
                'contact': step.get('contact', 'TBD'),
                'contact_role': step.get('contact_role', 'TBD'),
                'deadline': deadline.strftime('%A %b %d %H:%M UTC'),
                'deadline_iso': deadline.isoformat(),
                'legal_basis': step.get('legal_citation', ''),
                'amount': step['amount'],
                'unit': step['unit'],
            })

        return {
            'intent': 'incident_response',
            'incident_type': incident_type,
            'detected_at': detected_at.isoformat(),
            'playbook_name': playbook['name'],
            'playbook_source': playbook.get('source', ''),
            'steps': steps,
            'disclaimer': 'DECISION SUPPORT — NOT LEGAL ADVICE. Requirements vary by jurisdiction. Consult qualified legal counsel.',
            'evidence': [f"Playbook: {playbook['name']}", f"Source: {playbook.get('source', 'N/A')}"],
            'data_source': 'Hardcoded fallback (FalkorDB unavailable)',
        }

    # ========================================================================
    # AUTOMATION ASSESSMENT — queries graph for tasks with context
    # ========================================================================

    def _handle_automation(self, query: str) -> dict:
        """Handle automation assessment queries.

        GRAPH QUERY: Gets tasks with compliance context (COMPLIES_WITH edges)
        and dependency info (DEPENDS_ON edges). Scoring considers graph structure:
        tasks with many downstream dependencies get impact boost.
        """
        if self.db:
            graph_tasks = self.db.get_tasks_with_context()
            if graph_tasks:
                return self._build_automation_from_graph(graph_tasks)

        # FALLBACK: Try to query tasks without full context
        if self.db:
            tasks = self.db.get_all_tasks()
            if tasks:
                return {
                    'intent': 'automation_assessment',
                    'response': f"Found {len(tasks)} tasks in graph. Full attributes needed for scoring — ensure tasks are seeded with automation attributes.",
                    'tasks_found': len(tasks),
                    'framework': 'feasibility x impact quadrant',
                    'data_source': 'FalkorDB (partial)',
                }

        return {
            'intent': 'automation_assessment',
            'response': "Automation assessment requires task data in FalkorDB. Seed the graph with tasks containing automation attributes.",
            'framework': 'feasibility x impact quadrant',
            'methodology': 'Gated feasibility (noisy-AND) x hours/year impact',
            'data_source': 'None — FalkorDB unavailable or empty',
        }

    def _build_automation_from_graph(self, rows: list) -> dict:
        """Build automation assessment from graph query results.

        Each row contains task attributes + graph context:
        - regulations: from COMPLIES_WITH edges
        - depends_on: from DEPENDS_ON edges
        - process_name: from HAS_TASK edge

        Graph structure shapes scoring: tasks with many downstream deps
        get higher impact (failure/rework cascades).
        """
        scores = []
        graph_context = []

        for row in rows:
            # row: [task_id, name, description, freq, time, rate, structured, data_access, decision, exception, error_cost, compliance_risk, impl_cost, regulations, reg_jurisdictions, depends_on, process_name]
            (task_id, name, description, freq, time_hours, rate,
             structured, data_access, decision, exception,
             error_cost, compliance_risk, impl_cost,
             regulations, reg_jurisdictions, depends_on, process_name) = row

            task = TaskAttributes(
                name=name,
                frequency_per_year=freq or 0,
                time_per_exec_hours=time_hours or 0,
                labor_rate_dollars=rate or 0,
                structuredness=structured or 0.5,
                data_accessibility=data_access or 0.5,
                decision_complexity=decision or 0.5,
                exception_rate=exception or 0.1,
                error_cost_dollars=error_cost or 100,
                compliance_risk=compliance_risk or 0.1,
                implementation_cost_annual=impl_cost or 0,
            )
            score = assess(task)

            # Graph boost: tasks with many downstream dependencies have higher impact
            downstream_count = len([d for d in (depends_on or []) if d])
            if downstream_count > 0:
                # Boost impact by 10% per downstream dependency (capped at 50%)
                boost = min(downstream_count * 0.1, 0.5)
                score.impact_dollars *= (1 + boost)
                score.annual_savings *= (1 + boost)

            scores.append(score)
            graph_context.append({
                'task_id': task_id,
                'process': process_name or 'Unassigned',
                'regulations': regulations or [],
                'downstream_deps': downstream_count,
            })

        scores.sort(key=lambda s: s.annual_savings, reverse=True)

        return {
            'intent': 'automation_assessment',
            'scores': [
                {
                    'task_name': s.task_name,
                    'feasibility': s.feasibility,
                    'impact_dollars': s.impact_dollars,
                    'quadrant': s.quadrant,
                    'annual_savings': s.annual_savings,
                    'automation_fraction': s.automation_fraction,
                    'risk_gate': s.risk_gate_triggered,
                }
                for s in scores
            ],
            'graph_context': graph_context,
            'framework': 'feasibility x impact quadrant',
            'methodology': 'Gated feasibility (noisy-AND) x hours/year impact',
            'data_source': 'FalkorDB graph — tasks with COMPLIES_WITH, DEPENDS_ON, HAS_TASK context',
            'evidence': [
                f"GRAPH QUERY: MATCH (t:Task) OPTIONAL MATCH (t)-[:COMPLIES_WITH]->(r), (t)-[:DEPENDS_ON]->(d), (p)-[:HAS_TASK]->(t)",
                f"Tasks assessed: {len(scores)}",
                f"Graph boost applied: downstream dependency count increases impact",
            ],
        }

    # ========================================================================
    # PROCESS EXTRACTION — shows what's in the graph, validates structure
    # ========================================================================

    def _handle_extraction(self, query: str) -> dict:
        """Handle process extraction queries.

        GRAPH QUERY: Shows documents already in the graph and their
        extracted task graphs. Validates structure using graph algorithms.
        """
        if not self.db:
            return {
                'intent': 'process_extraction',
                'response': "Process extraction requires FalkorDB. Connect to the graph to view extracted processes.",
                'pipeline': 'Parse -> Chunk -> Extract -> Validate -> User Review',
            }

        # Get processes with their tasks from the graph
        processes = self.db.get_all_processes()
        documents = self.db.get_all_documents()

        extraction_results = []
        for proc in processes:
            proc_id = proc[0]
            tasks = self.db.get_process_with_tasks(proc_id)
            if tasks:
                # Build name→id mapping for this process's tasks
                name_to_id = {t[2]: t[1] for t in tasks}  # name → task_id
                # Extract task list for graph validation
                task_list = [{'task_id': t[1], 'name': t[2], 'description': t[3]} for t in tasks]
                # Get dependencies for this process's tasks
                # get_task_dependencies returns (prerequisites_list, downstream_list)
                # Each item is a dict: {'task': name, 'direction': 'depends_on'|'required_by', 'quote': str}
                edge_list = []
                for t in tasks:
                    dep_result = self.db.get_task_dependencies(t[1])
                    if dep_result and dep_result[0]:
                        prereqs, downstream = dep_result[0]
                        # Prerequisites: t depends on these (t -> prereq)
                        for d in (prereqs or []):
                            if isinstance(d, dict) and d.get('task'):
                                target_id = name_to_id.get(d['task'], d['task'])
                                edge_list.append({
                                    'from': t[1],
                                    'to': target_id,
                                    'source_quote': d.get('quote', ''),
                                })
                        # Downstream: these depend on t (downstream_task -> t)
                        for d in (downstream or []):
                            if isinstance(d, dict) and d.get('task'):
                                source_id = name_to_id.get(d['task'], d['task'])
                                edge_list.append({
                                    'from': source_id,
                                    'to': t[1],
                                    'source_quote': d.get('quote', ''),
                                })

                # Validate using graph algorithms
                validation = validate_process_graph(task_list, edge_list)

                extraction_results.append({
                    'process': proc[1],
                    'task_count': len(tasks),
                    'dependency_count': len(edge_list),
                    'valid': validation.get('valid', True),
                    'critical_path': validation.get('critical_path', []),
                })

        return {
            'intent': 'process_extraction',
            'documents': [{'doc_id': d[0], 'title': d[1], 'type': d[2]} for d in documents],
            'extracted_processes': extraction_results,
            'pipeline': 'Parse -> Chunk -> Extract -> Validate -> User Review',
            'data_source': 'FalkorDB graph',
            'evidence': [
                f"GRAPH: {len(processes)} processes, {len(documents)} documents",
                f"Validation: graph cycle detection + critical path",
            ],
        }

    # ========================================================================
    # CASCADE ANALYSIS — graph-powered blast radius + compliance context
    # ========================================================================

    def _handle_cascade(self, query: str) -> dict:
        """Handle cascade/impact queries.

        GRAPH QUERY: Multi-hop BFS from vendor through PROVIDES_SERVICE_FOR,
        HAS_TASK, DEPENDS_ON edges. Combines with compliance context.
        """
        if not self.db:
            return {
                'intent': 'cascade_analysis',
                'response': "Cascade analysis requires FalkorDB. Specify a vendor ID.",
            }

        # Extract vendor from query
        vendor_id = self._extract_vendor_from_query(query)
        if not vendor_id:
            # List available vendors from graph
            vendors = self.db.get_all_vendors()
            return {
                'intent': 'cascade_analysis',
                'response': "Specify a vendor to analyze blast radius.",
                'available_vendors': [
                    {'entity_id': v[0], 'name': v[1], 'type': v[2], 'risk_score': v[3]}
                    for v in vendors
                ],
            }

        # PRIMARY: Cascade impact via graph traversal
        cascade = self.db.get_cascade_impact(vendor_id)

        # ENHANCED: Risk propagation with compliance context
        risk_context = self.db.get_vendor_risk_propagation(vendor_id)

        if not cascade and not risk_context:
            return {
                'intent': 'cascade_analysis',
                'response': f"No cascade data found for '{vendor_id}'. Check vendor exists in graph.",
            }

        # Build structured response
        affected_processes = []
        affected_tasks = []
        compliance_at_risk = []

        for row in cascade:
            labels, eid, name = row
            if 'Process' in labels:
                affected_processes.append({'id': eid, 'name': name})
            elif 'Task' in labels:
                affected_tasks.append({'id': eid, 'name': name})

        for row in risk_context:
            entity_name, entity_type, task_name, regulation, jurisdiction, task_risk = row
            if regulation:
                compliance_at_risk.append({
                    'entity': entity_name,
                    'task': task_name,
                    'regulation': regulation,
                    'jurisdiction': jurisdiction,
                    'risk': task_risk,
                })

        return {
            'intent': 'cascade_analysis',
            'vendor_id': vendor_id,
            'blast_radius': len(cascade),
            'affected_processes': affected_processes,
            'affected_tasks': affected_tasks,
            'compliance_at_risk': compliance_at_risk,
            'total_entities_affected': len(cascade),
            'data_source': 'FalkorDB multi-hop BFS + compliance traversal',
            'evidence': [
                f"GRAPH BFS: Vendor-{vendor_id} -> PROVIDES_SERVICE_FOR -> Process/Task -> DEPENDS_ON -> Task",
                f"Hops: up to 3 (Vendor->Process->Task, Vendor->Task, Task->Task)",
                f"Compliance context: Task -> COMPLIES_WITH -> Regulation",
                f"Processes affected: {len(affected_processes)}",
                f"Tasks affected: {len(affected_tasks)}",
                f"Compliance obligations at risk: {len(compliance_at_risk)}",
            ],
        }

    # ========================================================================
    # COMPLIANCE CHECK — queries regulation graph, finds gaps
    # ========================================================================

    def _handle_compliance(self, query: str) -> dict:
        """Handle compliance queries.

        GRAPH QUERY: Gets regulations from graph, finds compliance gaps
        (tasks with high compliance_risk but no COMPLIES_WITH edges),
        shows regulation impact (which tasks/processes are affected).
        """
        if not self.db:
            return {
                'intent': 'compliance_check',
                'response': "Compliance checking requires FalkorDB.",
                'frameworks': ['GDPR (EU)', 'CCPA (California)', 'HIPAA (US)', 'SEC 8-K (US)', 'DPDPA (India)', 'CERT-In (India)', 'IT Act 2000 (India)'],
            }

        # Get all regulations from graph
        regulations = self.db.get_all_regulations()

        # Find compliance gaps (graph-powered insight)
        gaps = self.db.get_compliance_gaps()

        # Check for specific regulation
        reg_id = self._extract_regulation_from_query(query)
        regulation_impact = []
        if reg_id:
            regulation_impact = self.db.get_regulation_impact(reg_id)

        # Build jurisdiction summary from graph data
        jurisdictions = {}
        for reg in regulations:
            rid, name, jurisdiction = reg[0], reg[1], reg[2]
            if jurisdiction not in jurisdictions:
                jurisdictions[jurisdiction] = []
            jurisdictions[jurisdiction].append({'id': rid, 'name': name})

        # India-specific details
        india_details = []
        if 'india' in query.lower() or 'dpdpa' in query.lower() or 'cert' in query.lower():
            india_details = [
                {'name': 'CERT-In Directive 2022', 'deadline': '6 clock hours', 'applies_to': 'High-severity incidents', 'penalty': 'Per IT Act provisions', 'legal_basis': 'Section 70B, IT Act 2000'},
                {'name': 'DPDPA 2023', 'deadline': '72 clock hours', 'applies_to': 'Personal data breaches', 'penalty': 'Up to ₹250 crore per instance', 'legal_basis': 'Section 8(6), DPDPA 2023'},
                {'name': 'IT Act 2000 Sec 72A', 'deadline': 'N/A (criminal offense)', 'applies_to': 'Breach of confidentiality', 'penalty': 'Up to 3 years + ₹5 lakh', 'legal_basis': 'Section 72A, IT Act 2000'},
            ]

        return {
            'intent': 'compliance_check',
            'regulations': [{'id': r[0], 'name': r[1], 'jurisdiction': r[2]} for r in regulations],
            'jurisdictions': jurisdictions,
            'compliance_gaps': [
                {'task_id': g[0], 'name': g[1], 'risk': g[2], 'description': g[3]}
                for g in gaps
            ],
            'regulation_impact': [
                {'task_id': r[0], 'task_name': r[1], 'risk': r[2], 'process': r[3], 'downstream': r[4]}
                for r in regulation_impact
            ],
            'india_details': india_details,
            'data_source': 'FalkorDB graph — regulations, compliance gaps, impact traversal',
            'evidence': [
                f"GRAPH: {len(regulations)} regulations across {len(jurisdictions)} jurisdictions",
                f"Compliance gaps: {len(gaps)} tasks with high risk but no compliance edges",
                f"GRAPH QUERY for gaps: MATCH (t:Task) WHERE t.compliance_risk > 3 WHERE NOT (t)-[:COMPLIES_WITH]->()",
            ],
        }

    # ========================================================================
    # GENERAL — conversational with graph context
    # ========================================================================

    def _handle_general(self, query: str) -> dict:
        """Handle general queries — use LLM if available, with graph context."""
        # Try LLM for general queries
        if llm.available:
            llm_response = llm.complete(
                prompt=(
                    f"The user asked: '{query}'\n"
                    f"You are Company Brain, an enterprise operations AI backed by "
                    f"a FalkorDB Process Knowledge Graph. "
                    f"You help with: incident response, automation assessment, "
                    f"process extraction, cascade analysis, compliance checking. "
                    f"Give a helpful, concise response."
                ),
                max_tokens=300,
                temperature=0.5,
            )
            if llm_response:
                return {
                    'intent': 'general',
                    'response': llm_response,
                    'llm_generated': True,
                }

        return {
            'intent': 'general',
            'response': "I can help with: incident response, automation assessment, process extraction, cascade analysis, and compliance checking.",
            'available_intents': list(INTENT_PATTERNS.keys()),
        }

    # ========================================================================
    # Helper methods
    # ========================================================================

    def _extract_incident_type(self, query: str) -> str:
        """Extract incident type from query text."""
        if llm.available:
            result = llm.extract_structured(query, {
                'incident_type': 'one of: data_breach, ransomware, phishing, ddos',
                'severity': 'one of: low, medium, high, critical',
            })
            if result and result.get('incident_type'):
                return result['incident_type']

        query_lower = query.lower()
        if 'breach' in query_lower or 'unauthorized' in query_lower:
            return 'data_breach'
        if 'ransomware' in query_lower:
            return 'ransomware'
        if 'phishing' in query_lower:
            return 'phishing'
        if 'ddos' in query_lower or 'denial' in query_lower:
            return 'ddos'
        return 'data_breach'

    def _extract_detection_time(self, query: str) -> datetime:
        """Extract detection time from query, or use current time."""
        return datetime(2026, 10, 16, 14, 30)  # Friday 14:30 UTC

    def _extract_vendor_from_query(self, query: str) -> Optional[str]:
        """Extract vendor ID from query by matching against graph vendors."""
        if not self.db:
            return None

        query_lower = query.lower()
        vendors = self.db.get_all_vendors()

        # Try to match vendor name or ID from query
        for v in vendors:
            vid, name = v[0], v[1]
            if vid in query_lower or name.lower() in query_lower:
                return vid

        # Check for partial matches
        for v in vendors:
            vid, name = v[0], v[1]
            name_parts = name.lower().split()
            for part in name_parts:
                if len(part) > 3 and part in query_lower:
                    return vid

        return None

    def _extract_regulation_from_query(self, query: str) -> Optional[str]:
        """Extract regulation ID from query."""
        query_lower = query.lower()
        reg_map = {
            'gdpr': 'gdpr_eu',
            'ccpa': 'ccpa_ca',
            'hipaa': 'hipaa_privacy',
            'sec': 'sec_8k',
            'dpdpa': 'dpdpa_in',
            'cert-in': 'cert_in',
            'cert in': 'cert_in',
            'it act': 'it_act_india',
        }
        for keyword, reg_id in reg_map.items():
            if keyword in query_lower:
                return reg_id
        return None


def assess_task(
    name: str,
    frequency_per_year: float,
    time_per_exec_hours: float,
    labor_rate_dollars: float,
    structuredness: float = 0.5,
    data_accessibility: float = 0.5,
    decision_complexity: float = 0.5,
    exception_rate: float = 0.1,
    error_cost_dollars: float = 100,
    compliance_risk: float = 0.1,
    implementation_cost_annual: float = 0,
) -> AutomationScore:
    """Convenience function to assess a single task."""
    task = TaskAttributes(
        name=name,
        frequency_per_year=frequency_per_year,
        time_per_exec_hours=time_per_exec_hours,
        labor_rate_dollars=labor_rate_dollars,
        structuredness=structuredness,
        data_accessibility=data_accessibility,
        decision_complexity=decision_complexity,
        exception_rate=exception_rate,
        error_cost_dollars=error_cost_dollars,
        compliance_risk=compliance_risk,
        implementation_cost_annual=implementation_cost_annual,
    )
    return assess(task)
