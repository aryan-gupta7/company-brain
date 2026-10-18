"""Company Brain Agent — single agent with scoped tools.

Intent classification → tool selection → evidence assembly → response.
No multi-agent router. One agent handles all queries via tool selection.
"""

import sys; sys.path.insert(0, 'src')

from typing import List, Dict, Any, Optional
from core.deadline_calculator import compute_deadline
from core.automation_scoring import assess, TaskAttributes, AutomationScore
from core.graph_utils import validate_process_graph, compute_downstream_impact


# --- Intent classification (keyword-based, no LLM needed for routing) ---

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
    ],
    'compliance_check': [
        'compliant', 'compliance', 'regulation', 'deadline',
        'gdpr', 'ccpa', 'hipaa', 'obligation', 'requirement',
    ],
}


def classify_intent(query: str) -> str:
    """Classify user intent from query text.

    Simple keyword matching — no LLM needed for routing.
    Returns the most specific matching intent.
    """
    query_lower = query.lower()
    scores = {}

    for intent, patterns in INTENT_PATTERNS.items():
        score = sum(1 for p in patterns if p in query_lower)
        if score > 0:
            scores[intent] = score

    if not scores:
        return 'general'

    return max(scores, key=scores.get)


class CompanyBrainAgent:
    """Single agent that handles all Company Brain queries.

    Uses intent classification to select tools, then assembles responses
    with evidence paths.
    """

    def __init__(self, mcp_server=None, playbook_data: dict = None):
        self.mcp_server = mcp_server
        self.playbook_data = playbook_data or {}

    def handle(self, query: str) -> dict:
        """Handle a user query. Returns structured response with evidence."""
        intent = classify_intent(query)

        if intent == 'incident_response':
            return self._handle_incident(query)
        elif intent == 'automation_assessment':
            return self._handle_automation(query)
        elif intent == 'process_extraction':
            return self._handle_extraction(query)
        elif intent == 'cascade_analysis':
            return self._handle_cascade(query)
        elif intent == 'compliance_check':
            return self._handle_compliance(query)
        else:
            return self._handle_general(query)

    def _handle_incident(self, query: str) -> dict:
        """Handle incident response queries.

        Traverses curated playbook, computes deterministic deadlines.
        """
        # Extract incident type from query (simplified)
        incident_type = self._extract_incident_type(query)
        detected_at = self._extract_detection_time(query)

        playbook = self.playbook_data.get(incident_type)
        if not playbook:
            return {
                'intent': 'incident_response',
                'response': f"No curated playbook found for '{incident_type}'. Available: {list(self.playbook_data.keys())}",
                'evidence': [],
            }

        # Compute deadlines for each step
        steps = []
        for step in playbook['steps']:
            trigger_time = detected_at  # Simplified: all steps triggered at detection
            deadline = compute_deadline(
                trigger_time,
                step['amount'],
                step['unit'],
            )
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
            'disclaimer': '⚠️ DECISION SUPPORT — NOT LEGAL ADVICE. Requirements vary by jurisdiction. Consult qualified legal counsel.',
            'evidence': [f"Playbook: {playbook['name']}", f"Source: {playbook.get('source', 'N/A')}"],
        }

    def _handle_automation(self, query: str) -> dict:
        """Handle automation assessment queries."""
        return {
            'intent': 'automation_assessment',
            'response': "Automation assessment requires task data. Provide task attributes or upload an SOP document for extraction.",
            'framework': 'feasibility × impact quadrant',
            'methodology': 'Gated feasibility (noisy-AND) × hours/year impact',
        }

    def _handle_extraction(self, query: str) -> dict:
        """Handle process extraction queries."""
        return {
            'intent': 'process_extraction',
            'response': "Process extraction requires a document. Upload an SOP (PDF, Markdown, or text) to extract tasks and dependencies.",
            'pipeline': 'Parse → Chunk → Extract → Validate → User Review',
        }

    def _handle_cascade(self, query: str) -> dict:
        """Handle cascade/impact queries."""
        return {
            'intent': 'cascade_analysis',
            'response': "Cascade analysis requires a graph. Specify an entity ID to trace downstream impact.",
        }

    def _handle_compliance(self, query: str) -> dict:
        """Handle compliance queries."""
        return {
            'intent': 'compliance_check',
            'response': "Compliance checking requires regulation context. Specify jurisdiction and business type.",
            'frameworks': ['GDPR', 'CCPA', 'HIPAA'],
        }

    def _handle_general(self, query: str) -> dict:
        """Handle general queries."""
        return {
            'intent': 'general',
            'response': "I can help with: incident response, automation assessment, process extraction, cascade analysis, and compliance checking.",
            'available_intents': list(INTENT_PATTERNS.keys()),
        }

    def _extract_incident_type(self, query: str) -> str:
        """Extract incident type from query text."""
        query_lower = query.lower()
        if 'breach' in query_lower or 'unauthorized' in query_lower:
            return 'data_breach'
        if 'ransomware' in query_lower:
            return 'ransomware'
        if 'phishing' in query_lower:
            return 'phishing'
        if 'ddos' in query_lower or 'denial' in query_lower:
            return 'ddos'
        return 'data_breach'  # default

    def _extract_detection_time(self, query: str):
        """Extract detection time from query, or use current time."""
        from datetime import datetime
        # For the demo, use a fixed time
        # In production, parse from query or use datetime.now()
        return datetime(2026, 10, 16, 14, 30)  # Friday 14:30 UTC


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
