from nexus.project.guide import ProjectGuide
from nexus.project.interface_registry import InterfaceRegistry

def test_register_interface(tmp_path):
    guide_file = tmp_path / "PROJECT_GUIDE.md"
    guide = ProjectGuide(guide_path=str(guide_file))
    
    # Initialize the guide with empty registry
    guide.update_section("## Interface Registry", "")
    
    registry = InterfaceRegistry(guide)
    registry.register_interface(
        file_path="src/models/user.py",
        function_signature="def create_user(username: str) -> dict",
        description="Returns user dict"
    )
    
    interfaces = registry.get_interfaces_for_file("src/models/user.py")
    assert len(interfaces) == 1
    assert interfaces[0][0] == "def create_user(username: str) -> dict"
    assert interfaces[0][1] == "Returns user dict"

def test_update_existing_interface(tmp_path):
    guide_file = tmp_path / "PROJECT_GUIDE.md"
    guide = ProjectGuide(guide_path=str(guide_file))
    guide.update_section("## Interface Registry", "")
    
    registry = InterfaceRegistry(guide)
    registry.register_interface(
        file_path="src/models/user.py",
        function_signature="def create_user(username: str) -> dict",
        description="Returns user dict"
    )
    
    # Update same function signature/description
    registry.register_interface(
        file_path="src/models/user.py",
        function_signature="def create_user(username: str, role: str = 'user') -> dict",
        description="Returns user dict with role"
    )
    
    interfaces = registry.get_interfaces_for_file("src/models/user.py")
    assert len(interfaces) == 1
    assert interfaces[0][0] == "def create_user(username: str, role: str = 'user') -> dict"
    assert interfaces[0][1] == "Returns user dict with role"
