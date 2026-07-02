import os
import tempfile
from nexus.agent.verifier import Verifier

def test_verifier_syntax_checks():
    with tempfile.TemporaryDirectory() as tmpdir:
        verifier = Verifier(tmpdir)
        
        # Valid Python
        file_path = "valid.py"
        with open(os.path.join(tmpdir, file_path), "w") as f:
            f.write("def foo():\n    return 42\n")
        ok, err = verifier.verify_syntax(file_path)
        assert ok is True
        
        # Invalid Python
        bad_file = "bad.py"
        with open(os.path.join(tmpdir, bad_file), "w") as f:
            f.write("def foo(\n")
        ok, err = verifier.verify_syntax(bad_file)
        assert ok is False
        assert "SyntaxError" in err

def test_verifier_pytest_allow_empty():
    with tempfile.TemporaryDirectory() as tmpdir:
        verifier = Verifier(tmpdir)
        # Directory "tests" doesn't exist, should pass due to code 4 exemption
        ok, out = verifier.run_tests("tests")
        assert ok is True

def test_verifier_verify_importable():
    with tempfile.TemporaryDirectory() as tmpdir:
        verifier = Verifier(tmpdir)
        
        # Valid python (no imports)
        file_path = "valid.py"
        with open(os.path.join(tmpdir, file_path), "w") as f:
            f.write("def foo():\n    return 42\n")
        ok, err = verifier.verify_importable(file_path)
        assert ok is True
        
        # Invalid python (bad import at runtime)
        bad_file = "bad.py"
        with open(os.path.join(tmpdir, bad_file), "w") as f:
            f.write("import non_existent_module_foo_bar\n")
        ok, err = verifier.verify_importable(bad_file)
        assert ok is False
        assert "ImportError" in err

