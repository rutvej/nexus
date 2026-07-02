import tempfile
from nexus.project.guide import ProjectGuide
from nexus.project.interface_registry import InterfaceRegistry

def test_interface_registry_flow():
    with tempfile.TemporaryDirectory() as tmpdir:
        guide = ProjectGuide(workspace_path=tmpdir)
        reg = InterfaceRegistry(guide)
        
        # Test add and save
        reg.add_signature("src/math.py", "def add(a: int, b: int) -> int", "Add two integers")
        reg.add_signature("src/math.py", "def sub(a: int, b: int) -> int", "Subtract two integers")
        reg.add_signature("src/auth.py", "def login()", "User login")
        reg.save()
        
        # Re-read and verify parsing works
        reg2 = InterfaceRegistry(guide)
        assert "src/math.py" in reg2.registry
        assert len(reg2.registry["src/math.py"]) == 2
        assert reg2.registry["src/math.py"][0]["signature"] == "def add(a: int, b: int) -> int"
        
        # Test related interfaces
        related = reg2.get_related_interfaces("src/math.py")
        assert "src/auth.py" in related
        assert "src/math.py" not in related
