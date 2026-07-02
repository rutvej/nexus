import tempfile
from pathlib import Path
from nexus.project.guide import ProjectGuide

def test_project_guide_sections():
    with tempfile.TemporaryDirectory() as tmpdir:
        guide = ProjectGuide(workspace_path=tmpdir)
        
        # Test default contents exist
        content = guide.read()
        assert "# PROJECT GUIDE" in content
        assert "## Tech Stack" in content
        
        # Test get section
        tech_section = guide.get_section("Tech Stack")
        assert "Tech Stack" in tech_section
        
        # Test update section
        guide.update_section("## Tech Stack", "## Tech Stack\n- Python\n- Flask")
        updated = guide.get_section("Tech Stack")
        assert "- Flask" in updated
