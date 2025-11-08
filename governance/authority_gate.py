from .constitution import CONSTITUTION

def check_authority(action: str):
    """Return True if Sky is allowed to perform this action, else False."""
    if action in CONSTITUTION["allowed"]:
        return True
    if action in CONSTITUTION["restricted"]:
        return False
    # default-deny for undefined actions
    return False


# Later this will auto-trigger refusal messages + escalation routing.
