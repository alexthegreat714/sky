"""
Constitutional authority gate tests (Phase 3 scaffold)

Will test:
- Allowed action approval
- Restricted action denial
- Default-deny for undefined actions
- Escalation path routing
"""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from governance import authority_gate


def test_allowed_actions():
    """Test that allowed actions pass authority check"""
    allowed = [
        "answer_questions",
        "run_approved_tools",
        "store_memories",
        "generate_reports"
    ]

    for action in allowed:
        assert authority_gate.check_authority(action) is True, \
            f"Action '{action}' should be allowed"


def test_restricted_actions():
    """Test that restricted actions are denied"""
    restricted = [
        "modify_system_configs",
        "restart_services",
        "edit_other_agents_memory",
        "financial_transactions",
        "self_upgrade"
    ]

    for action in restricted:
        assert authority_gate.check_authority(action) is False, \
            f"Action '{action}' should be restricted"


def test_undefined_actions_default_deny():
    """Test that undefined actions default to denied"""
    undefined = [
        "hack_mainframe",
        "launch_missiles",
        "time_travel",
        "arbitrary_code_execution"
    ]

    for action in undefined:
        assert authority_gate.check_authority(action) is False, \
            f"Undefined action '{action}' should default to denied"


def test_boundary_cases():
    """Test edge cases"""
    # Empty string
    assert authority_gate.check_authority("") is False

    # Case sensitivity (current implementation is case-sensitive)
    assert authority_gate.check_authority("ANSWER_QUESTIONS") is False
    assert authority_gate.check_authority("answer_questions") is True


if __name__ == "__main__":
    print("Running constitutional gate tests...")

    test_allowed_actions()
    print("✓ test_allowed_actions passed")

    test_restricted_actions()
    print("✓ test_restricted_actions passed")

    test_undefined_actions_default_deny()
    print("✓ test_undefined_actions_default_deny passed")

    test_boundary_cases()
    print("✓ test_boundary_cases passed")

    print("\nAll constitutional gate tests passed! (Phase 3 scaffold)")
