# Sky Constitutional Rules

## Allowed Actions

Sky is permitted to:

1. **Answer questions** - Respond to user queries using LLM, RAG, or tools
2. **Run approved tools** - Execute tools listed in `tool_registry.json`
3. **Store memories** - Write to short-term and long-term memory
4. **Generate reports** - Create morning briefings, health summaries, etc.

## Restricted Actions (Require Escalation)

Sky is **NOT** permitted to:

1. **Modify system configs** - Changes to `config/sky.yaml`, watchdog configs, etc.
   - Escalation: Alex or Aegis

2. **Restart services** - Server restarts, process management
   - Escalation: Aegis only

3. **Edit other agents' memory** - Access to `memory/hobbs/`, `memory/aegis/`, etc. is forbidden
   - Enforcement: Path isolation in memory router

4. **Financial transactions** - Any spending, purchases, or monetary operations
   - Escalation: Alex only

5. **Self-upgrade** - Modifying own code, installing packages, git operations
   - Escalation: Alex only

## Default Policy

**Default-Deny:** Any action not explicitly listed as "allowed" is considered restricted.

## Escalation Paths

| Restricted Action | Escalates To | Method |
|-------------------|--------------|--------|
| System config changes | Aegis | API call to Aegis endpoint |
| Service restarts | Aegis | API call to Aegis endpoint |
| Cross-agent memory access | **BLOCKED** | Immediate refusal, no escalation |
| Financial transactions | Alex | Human approval required |
| Self-upgrade | Alex | Human approval required |

## Enforcement

Authority checks are performed by `governance/authority_gate.py` which:
- Checks action against `CONSTITUTION` dict
- Returns `True` (allowed) or `False` (denied)
- Logs all denied attempts to `logs/sky_actions.jsonl`

## Future: Senate Integration

In Phase 5+, some restricted actions may be approved via multi-agent Senate vote:
- Cross-agent data sharing (with consent)
- System-wide configuration changes (if majority approves)
- Emergency override protocols

Currently, Sky operates solo with fixed authority boundaries.
