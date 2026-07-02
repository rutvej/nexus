import os
from nexus.project.guide import ProjectGuide

def test_project_guide_init(tmp_path):
    guide_file = tmp_path / "PROJECT_GUIDE.md"
    guide = ProjectGuide(guide_path=str(guide_file))
    
    assert guide_file.exists()
    content = guide.read()
    assert "# Nexus Project Guide" in content
    assert "## 1. Technology Stack" in content

def test_project_guide_update_existing_section(tmp_path):
    guide_file = tmp_path / "PROJECT_GUIDE.md"
    guide = ProjectGuide(guide_path=str(guide_file))
    
    # Update "## 3. Active Schemas"
    guide.update_section("## 3. Active Schemas", "- users table\n- tweets table")
    
    content = guide.read()
    assert "- users table" in content
    assert "- tweets table" in content
    # Verify the next section still exists
    assert "## 4. Architectural Conventions" in content

def test_project_guide_append_new_section(tmp_path):
    guide_file = tmp_path / "PROJECT_GUIDE.md"
    guide = ProjectGuide(guide_path=str(guide_file))
    
    guide.update_section("## Interface Registry", "### src/user.py\n- create_user")
    
    content = guide.read()
    assert "## Interface Registry" in content
    assert "- create_user" in content
