from src.governance.authority_gate import check_authority

def test_basic_allows():
    assert check_authority("answer_questions") is True

def test_basic_denies():
    assert check_authority("restart_services") is False
