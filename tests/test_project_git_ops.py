import tempfile
import os
import subprocess
from nexus.project.git_ops import GitOperations

def test_git_ops_flow():
    with tempfile.TemporaryDirectory() as tmpdir:
        # Initialize git repo in tmpdir
        subprocess.run(["git", "init"], cwd=tmpdir, capture_output=True)
        # Set dummy config for git
        subprocess.run(["git", "config", "user.name", "Test"], cwd=tmpdir)
        subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=tmpdir)
        
        git = GitOperations(repo_path=tmpdir)
        
        # Initial commit so HEAD exists
        test_file = os.path.join(tmpdir, "initial.txt")
        with open(test_file, "w") as f:
            f.write("initial content")
        git._run_git(["add", "."])
        git._run_git(["commit", "-m", "initial", "--author=Test <test@example.com>"])
        
        h1 = git.get_current_head_hash()
        assert len(h1) > 0
        
        # Test commit ticket changes
        new_file = os.path.join(tmpdir, "new.txt")
        with open(new_file, "w") as f:
            f.write("new content")
        h2 = git.commit_ticket_changes("T-1", "Add new file")
        assert h1 != h2
        
        # Test tag checkpoint
        tag = git.create_checkpoint_tag()
        assert tag.startswith("checkpoint-")
        
        # Test rollback changes
        dirty_file = os.path.join(tmpdir, "dirty.txt")
        with open(dirty_file, "w") as f:
            f.write("dirty content")
        git.rollback_changes()
        assert not os.path.exists(dirty_file)

def test_git_ops_fresh_init():
    with tempfile.TemporaryDirectory() as tmpdir:
        # Instantiating on raw directory without calling git init
        git = GitOperations(repo_path=tmpdir)
        
        # Verify .git directory now exists
        assert os.path.exists(os.path.join(tmpdir, ".git"))
        
        # Verify branch is checked out via git status
        status = git._run_git(["status"])
        assert "On branch nexus/main" in status or "Initial commit" in status or "No commits yet" in status
