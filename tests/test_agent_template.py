from src.agents.hobbs.main import describe

def test_hobbs_describe():
    d = describe()
    assert d["name"] == "Hobbs"
