"""Authority checking scaffold. Default-deny for undefined actions."""
from .constitution import CONSTITUTION

def check_authority(action: str) -> bool:
    if action in CONSTITUTION["allowed"]:
        return True
    if action in CONSTITUTION["restricted"]:
        return False
    return False  # default deny

def refusal_message(action: str) -> str:
    esc = CONSTITUTION.get("escalation", {})
    owner = esc.get("owner", "owner")
    override = esc.get("override_agent", "aegis")
    return (f'⚠️ Action blocked: "{action}" exceeds Sky\'s authority. '
            f'Escalate to {override} or {owner}.')
