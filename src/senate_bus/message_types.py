from dataclasses import dataclass
from typing import Dict, Any

@dataclass
class ActionRequest:
    sender: str
    action: str
    payload: Dict[str, Any]

@dataclass
class VotePacket:
    topic: str
    options: Dict[str, float]  # option -> score
    quorum: int = 3
