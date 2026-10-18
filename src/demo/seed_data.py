"""Seed data for Company Brain demo.

Curated playbook data (NOT extracted from documents).
Uses StepTemplate label to prevent ingestion from modifying playbooks.
"""

from datetime import datetime


# --- Playbook: Data Breach Response ---
# Source: NIST SP 800-61 Rev. 2
# Deadlines: GDPR Art. 33 (72h from awareness), GDPR Art. 48 (48h from awareness)

DATA_BREACH_PLAYBOOK = {
    'playbook_id': 'pb_data_breach',
    'name': 'Data Breach Response',
    'incident_type': 'data_breach',
    'version': '1.0',
    'last_reviewed': '2026-10-01',
    'source': 'NIST SP 800-61 Rev. 2',
    'steps': [
        {
            'step_id': 'step_isolate',
            'name': 'Isolate Affected Systems',
            'order': 1,
            'amount': 0,
            'unit': 'clock_hours',
            'trigger': 'detection',
            'contact': 'Sarah Chen',
            'contact_role': 'CISO',
            'legal_citation': None,
        },
        {
            'step_id': 'step_forensics',
            'name': 'Engage External Forensics',
            'order': 2,
            'amount': 1,
            'unit': 'clock_hours',
            'trigger': 'detection',
            'contact': 'SecureCorp IR Team',
            'contact_role': 'External Forensics',
            'legal_citation': None,
        },
        {
            'step_id': 'step_legal_hold',
            'name': 'Issue Legal Hold',
            'order': 3,
            'amount': 2,
            'unit': 'clock_hours',
            'trigger': 'detection',
            'contact': 'James Wilson',
            'contact_role': 'General Counsel',
            'legal_citation': None,
        },
        {
            'step_id': 'step_gdpr_assess',
            'name': 'GDPR Breach Assessment',
            'order': 4,
            'amount': 24,
            'unit': 'clock_hours',
            'trigger': 'detection',
            'contact': 'Maria Garcia',
            'contact_role': 'DPO',
            'legal_citation': 'GDPR Art. 33: 72 hours from awareness',
        },
        {
            'step_id': 'step_gdpr_file',
            'name': 'GDPR Regulatory Filing',
            'order': 5,
            'amount': 72,
            'unit': 'clock_hours',
            'trigger': 'awareness',
            'contact': 'Maria Garcia',
            'contact_role': 'DPO',
            'legal_citation': 'GDPR Art. 33: 72 hours from awareness — file with supervisory authority',
        },
        {
            'step_id': 'step_notify',
            'name': 'Customer Notification',
            'order': 6,
            'amount': 48,
            'unit': 'clock_hours',
            'trigger': 'awareness',
            'contact': 'Alex Rivera',
            'contact_role': 'VP Marketing',
            'legal_citation': 'GDPR Art. 34: without undue delay if high risk to individuals',
        },
    ],
}


# --- Playbook: Ransomware Response ---
RANSOMWARE_PLAYBOOK = {
    'playbook_id': 'pb_ransomware',
    'name': 'Ransomware Response',
    'incident_type': 'ransomware',
    'version': '1.0',
    'last_reviewed': '2026-10-01',
    'source': 'NIST SP 800-61 Rev. 2',
    'steps': [
        {
            'step_id': 'step_rw_isolate',
            'name': 'Isolate Network Segments',
            'order': 1,
            'amount': 0,
            'unit': 'clock_hours',
            'trigger': 'detection',
            'contact': 'Sarah Chen',
            'contact_role': 'CISO',
            'legal_citation': None,
        },
        {
            'step_id': 'step_rw_assess',
            'name': 'Assess Scope of Infection',
            'order': 2,
            'amount': 2,
            'unit': 'clock_hours',
            'trigger': 'detection',
            'contact': 'Sarah Chen',
            'contact_role': 'CISO',
            'legal_citation': None,
        },
        {
            'step_id': 'step_rw_gdpr',
            'name': 'GDPR Breach Assessment',
            'order': 3,
            'amount': 24,
            'unit': 'clock_hours',
            'trigger': 'detection',
            'contact': 'Maria Garcia',
            'contact_role': 'DPO',
            'legal_citation': 'GDPR Art. 33: 72 hours from awareness',
        },
    ],
}


# --- All playbooks ---
PLAYBOOKS = {
    'data_breach': DATA_BREACH_PLAYBOOK,
    'ransomware': RANSOMWARE_PLAYBOOK,
}


# --- Cypher seed statements for FalkorDB ---
# Creates the playbook graph with StepTemplate nodes (not Task)

SEED_CYPHER = """
// Create playbook
CREATE (pb:Playbook {
  playbook_id: 'pb_data_breach',
  name: 'Data Breach Response',
  incident_type: 'data_breach',
  version: '1.0',
  last_reviewed: '2026-10-01',
  source_citation: 'NIST SP 800-61 Rev. 2'
})

// Create step templates (StepTemplate label, NOT Task)
CREATE (s1:StepTemplate {step_id: 'step_isolate', name: 'Isolate Affected Systems', contact_role: 'CISO'})
CREATE (s2:StepTemplate {step_id: 'step_forensics', name: 'Engage External Forensics', contact_role: 'External_Forensics'})
CREATE (s3:StepTemplate {step_id: 'step_legal_hold', name: 'Issue Legal Hold', contact_role: 'General_Counsel'})
CREATE (s4:StepTemplate {step_id: 'step_gdpr_assess', name: 'GDPR Breach Assessment', contact_role: 'DPO'})
CREATE (s5:StepTemplate {step_id: 'step_gdpr_file', name: 'GDPR Regulatory Filing', contact_role: 'DPO'})
CREATE (s6:StepTemplate {step_id: 'step_notify', name: 'Customer Notification', contact_role: 'VP_Marketing'})

// Link playbook to steps (deadline metadata on edges only)
CREATE (pb)-[:HAS_STEP {order: 1, amount: 0, unit: 'clock_hours', trigger: 'detection'}]->(s1)
CREATE (pb)-[:HAS_STEP {order: 2, amount: 1, unit: 'clock_hours', trigger: 'detection'}]->(s2)
CREATE (pb)-[:HAS_STEP {order: 3, amount: 2, unit: 'clock_hours', trigger: 'detection'}]->(s3)
CREATE (pb)-[:HAS_STEP {order: 4, amount: 24, unit: 'clock_hours', trigger: 'detection', legal_citation: 'GDPR Art. 33: 72 hours from awareness'}]->(s4)
CREATE (pb)-[:HAS_STEP {order: 5, amount: 72, unit: 'clock_hours', trigger: 'awareness', legal_citation: 'GDPR Art. 33: 72 hours from awareness'}]->(s5)
CREATE (pb)-[:HAS_STEP {order: 6, amount: 48, unit: 'clock_hours', trigger: 'awareness', legal_citation: 'GDPR Art. 34: without undue delay if high risk'}]->(s6)

// Create contacts
CREATE (ciso:Person {person_id: 'p_ciso', name: 'Sarah Chen', role: 'CISO', department: 'Engineering'})
CREATE (gc:Person {person_id: 'p_gc', name: 'James Wilson', role: 'General Counsel', department: 'Legal'})
CREATE (dpo:Person {person_id: 'p_dpo', name: 'Maria Garcia', role: 'DPO', department: 'Legal'})
CREATE (sec:Person {person_id: 'p_sec', name: 'SecureCorp IR Team', role: 'External_Forensics', department: 'External'})
CREATE (vp:Person {person_id: 'p_vp', name: 'Alex Rivera', role: 'VP_Marketing', department: 'Marketing'})

// Link contacts to steps
CREATE (s1)-[:CONTACT]->(ciso)
CREATE (s2)-[:CONTACT]->(sec)
CREATE (s3)-[:CONTACT]->(gc)
CREATE (s4)-[:CONTACT]->(dpo)
CREATE (s5)-[:CONTACT]->(dpo)
CREATE (s6)-[:CONTACT]->(vp)

// Create vector indexes (384-dim for all-MiniLM-L6-v2)
CREATE VECTOR INDEX FOR (t:Task) ON (t.embedding) OPTIONS {dimension: 384, similarityFunction: 'cosine'}
CREATE VECTOR INDEX FOR (d:Document) ON (d.embedding) OPTIONS {dimension: 384, similarityFunction: 'cosine'}
CREATE VECTOR INDEX FOR (p:Person) ON (p.embedding) OPTIONS {dimension: 384, similarityFunction: 'cosine'}
CREATE VECTOR INDEX FOR (i:Incident) ON (i.embedding) OPTIONS {dimension: 384, similarityFunction: 'cosine'}
"""


# --- Demo company: processes and tasks ---

DEMO_TASKS = [
    {
        'task_id': 't_invoice_recon',
        'name': 'Invoice Reconciliation',
        'description': 'Match received invoices against purchase orders and payment records',
        'frequency_per_year': 52,
        'time_per_exec_hours': 3.85,
        'structuredness': 0.9,
        'data_accessibility': 0.95,
        'decision_complexity': 0.2,
        'exception_rate': 0.1,
        'error_cost_dollars': 500,
        'compliance_risk': 0.1,
        'labor_rate_dollars': 42,
        'implementation_cost_annual': 1200,
    },
    {
        'task_id': 't_expense_report',
        'name': 'Expense Report Review',
        'description': 'Review and approve employee expense reports',
        'frequency_per_year': 24,
        'time_per_exec_hours': 1.5,
        'structuredness': 0.7,
        'data_accessibility': 0.8,
        'decision_complexity': 0.4,
        'exception_rate': 0.3,
        'error_cost_dollars': 200,
        'compliance_risk': 0.2,
        'labor_rate_dollars': 35,
        'implementation_cost_annual': 800,
    },
    {
        'task_id': 't_strategy_review',
        'name': 'Executive Strategy Review',
        'description': 'Quarterly strategic planning and market analysis',
        'frequency_per_year': 4,
        'time_per_exec_hours': 8,
        'structuredness': 0.2,
        'data_accessibility': 0.3,
        'decision_complexity': 0.9,
        'exception_rate': 0.8,
        'error_cost_dollars': 50000,
        'compliance_risk': 0.1,
        'labor_rate_dollars': 150,
        'implementation_cost_annual': 0,
    },
    {
        'task_id': 't_data_entry',
        'name': 'Customer Data Entry',
        'description': 'Enter customer information from forms into CRM',
        'frequency_per_year': 260,
        'time_per_exec_hours': 0.5,
        'structuredness': 0.95,
        'data_accessibility': 0.9,
        'decision_complexity': 0.1,
        'exception_rate': 0.05,
        'error_cost_dollars': 100,
        'compliance_risk': 0.3,
        'labor_rate_dollars': 25,
        'implementation_cost_annual': 600,
    },
]


def get_playbook(incident_type: str) -> dict:
    """Get a curated playbook by incident type."""
    return PLAYBOOKS.get(incident_type)


def get_demo_tasks() -> list:
    """Get demo tasks for automation assessment."""
    return DEMO_TASKS
