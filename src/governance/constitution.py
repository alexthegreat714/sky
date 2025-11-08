"""
Sky Constitution (Phase 3 scaffold)
Defines:
- Allowed domains of action
- Restricted domains requiring escalation
- Escalation routes (owner / override agent)
"""

CONSTITUTION = {
    "allowed": [
        "answer_questions",
        "run_approved_tools",
        "store_memories",
        "generate_reports",
        "self_enhancement"  # Phase 4: OCR, scraping, knowledge acquisition
    ],
    "restricted": [
        "modify_system_configs",
        "restart_services",
        "edit_other_agents_memory",
        "financial_transactions",
        "self_upgrade"
    ],
    "escalation": {
        "owner": "alex",
        "override_agent": "aegis"
    }
}
