from src.memory.manager import remember_short, remember_long_export

def test_short_memory():
    rec = remember_short("stub note", tags=["t"], importance=0.2)
    assert rec["type"] == "short"

def test_long_export():
    rec = remember_long_export("persistent note", tags=["p"], importance=0.9)
    assert rec["type"] == "long"
