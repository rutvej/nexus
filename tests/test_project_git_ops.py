import os
import subprocess
from nexus.project.git_ops import GitOperations

def test_git_ops(tmp_path):
    # Initialize a dummy git repo in tmp_path
    subprocess.run(["git", "init"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=tmp_path, check=True)
    subprocess.run(["git", "checkout", "-b", "nexus/experiment-001"], cwd=tmp_path, check=True)

    git_ops = GitOperations(repo_path=str(tmp_path))
    
    # 1. Test get_current_head_hash on empty repo
    assert git_ops.get_current_head_hash() == ""

    # Create a file and commit it
    test_file = tmp_path / "hello.txt"
    test_file.write_text("hello world")
    
    # 2. Test commit_ticket_changes
    commit_hash = git_ops.commit_ticket_changes("T1", "Initial Commit")
    assert commit_hash != ""
    assert len(commit_hash) == 40
    assert git_ops.get_current_head_hash() == commit_hash

    # 3. Test tag creation
    tag = git_ops.create_checkpoint_tag()
    assert tag.startswith("checkpoint-")

    # Modify file and test rollback
    test_file.write_text("modified")
    new_file = tmp_path / "new.txt"
    new_file.write_text("untracked")
    
    # 4. Test rollback_changes
    git_ops.rollback_changes()
    assert test_file.read_text() == "hello world"
    assert not new_file.exists()
