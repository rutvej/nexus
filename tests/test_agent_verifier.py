import os
from nexus.agent.verifier import Verifier

def test_verify_syntax_valid(tmp_path):
    f = tmp_path / "valid.py"
    f.write_text("def add(a, b):\n    return a + b\n")
    
    verifier = Verifier(workspace_dir=str(tmp_path))
    success, err = verifier.verify_syntax("valid.py")
    assert success is True
    assert err == ""

def test_verify_syntax_invalid(tmp_path):
    f = tmp_path / "invalid.py"
    f.write_text("def add(a, b):\n    return a +\n") # Syntax error
    
    verifier = Verifier(workspace_dir=str(tmp_path))
    success, err = verifier.verify_syntax("invalid.py")
    assert success is False
    assert "SyntaxError" in err

def test_auto_format(tmp_path):
    f = tmp_path / "unformatted.py"
    f.write_text("def add(a,b):return a+b\n") # Bad formatting
    
    verifier = Verifier(workspace_dir=str(tmp_path))
    assert verifier.check_formatting("unformatted.py") is False
    
    assert verifier.auto_format("unformatted.py") is True
    assert verifier.check_formatting("unformatted.py") is True

def test_run_tests_success(tmp_path):
    test_f = tmp_path / "test_success.py"
    test_f.write_text("def test_dummy():\n    assert 1 == 1\n")
    
    verifier = Verifier(workspace_dir=str(tmp_path))
    success, out = verifier.run_tests("test_success.py")
    assert success is True

def test_run_tests_failure(tmp_path):
    test_f = tmp_path / "test_failure.py"
    test_f.write_text("def test_dummy():\n    assert 1 == 2\n")
    
    verifier = Verifier(workspace_dir=str(tmp_path))
    success, out = verifier.run_tests("test_failure.py")
    assert success is False
    assert "AssertionError" in out
