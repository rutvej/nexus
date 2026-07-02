import sys
from unittest.mock import patch, MagicMock
from nexus.sandbox.docker_runner import DockerRunner

def test_runner_local_fallback(tmp_path):
    runner = DockerRunner(workspace_dir=str(tmp_path))
    
    # We patch is_docker_available to return False to test local fallback execution
    with patch.object(runner, 'is_docker_available', return_value=False):
        # We run a simple python command that prints "hello" using sys.executable
        code, stdout, stderr = runner.run_in_sandbox([sys.executable, "-c", "print('hello')"])
        assert code == 0
        assert "hello" in stdout

def test_runner_docker_execution(tmp_path):
    runner = DockerRunner(workspace_dir=str(tmp_path))
    
    # Mocking is_docker_available and _run_command to check that docker run is invoked correctly
    with patch.object(runner, 'is_docker_available', return_value=True), \
         patch.object(runner, '_run_command') as mock_run:
        
        mock_run.return_value = (0, "output", "")
        
        runner.run_in_sandbox(["pytest"])
        
        # Verify it constructed the docker command correctly
        args, kwargs = mock_run.call_args
        docker_cmd = args[0]
        assert "docker" in docker_cmd
        assert "run" in docker_cmd
        assert "--network=none" in docker_cmd
        assert "pytest" in docker_cmd
