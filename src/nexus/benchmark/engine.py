from typing import List, Tuple
from nexus.benchmark.tasks import TASKS
from nexus.benchmark.runner import run_evaluation, DEFAULT_OLLAMA_URL, CUSTOM_OLLAMA_URL
from nexus.models.router import ModelRouter

class BenchmarkEngine:
    def __init__(self, router: ModelRouter):
        self.router = router

    def run_all(self) -> str:
        """Run benchmark suite for all available models."""
        models_to_evaluate = []
        
        # Determine which models are running/available
        for model_name, profile in self.router.scores.items():
            host = profile["host"]
            backend = self.router.backends.get(host)
            if backend and backend.is_available():
                models_to_evaluate.append((model_name, host))
                
        if not models_to_evaluate:
            raise RuntimeError("No Ollama models are currently available to benchmark.")
            
        # Run using the evaluation runner we built earlier
        run_id = run_evaluation(models_to_evaluate, TASKS)
        
        # Reload scores in the router
        self.router.load_scores()
        
        return run_id
