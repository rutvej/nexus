import json
import time
import urllib.request
import urllib.error
import uuid
from typing import List, Dict, Any, Tuple
from nexus.benchmark.tasks import BenchmarkTask, TASKS
from nexus.benchmark.evaluator import evaluate_task
from nexus.benchmark.database import record_run, record_result, update_model_score

DEFAULT_OLLAMA_URL = "http://localhost:11434"
CUSTOM_OLLAMA_URL = "http://localhost:11435"

def query_ollama(model_name: str, prompt: str, host_url: str = DEFAULT_OLLAMA_URL) -> Dict[str, Any]:
    """Query local Ollama server using urllib (standard library)."""
    url = f"{host_url}/api/generate"
    data = {
        "model": model_name,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": 0.1,
            "seed": 42
        }
    }
    
    headers = {"Content-Type": "application/json"}
    req_body = json.dumps(data).encode("utf-8")
    
    req = urllib.request.Request(url, data=req_body, headers=headers, method="POST")
    
    start_time = time.time()
    try:
        with urllib.request.urlopen(req, timeout=300) as response:
            resp_body = response.read().decode("utf-8")
            duration_ms = (time.time() - start_time) * 1000
            resp_data = json.loads(resp_body)
            resp_data["latency_ms"] = duration_ms
            return resp_data
    except urllib.error.URLError as e:
        raise RuntimeError(f"Ollama query failed on {url} for model {model_name}: {e}")

def run_evaluation(models_to_evaluate: List[Tuple[str, str]], tasks_to_run: List[BenchmarkTask]) -> str:
    """
    Run evaluation for specified models and tasks.
    models_to_evaluate: list of tuples (model_name, host_url)
    """
    run_id = str(uuid.uuid4())
    record_run(run_id)
    
    print(f"Starting evaluation run {run_id}...")
    print(f"Evaluating {len(models_to_evaluate)} models on {len(tasks_to_run)} tasks.")
    print("-" * 60)
    
    for model_name, host_url in models_to_evaluate:
        print(f"Model: {model_name} (Host: {host_url})")
        for task in tasks_to_run:
            print(f"  Running task: {task.id} ({task.name})...", end="", flush=True)
            
            try:
                # Query Ollama
                resp = query_ollama(model_name, task.prompt, host_url)
                raw_output = resp.get("response", "")
                latency_ms = resp.get("latency_ms", 0.0)
                tokens_prompt = resp.get("prompt_eval_count", 0)
                tokens_gen = resp.get("eval_count", 0)
                
                # Evaluate output
                success, details = evaluate_task(task, raw_output)
                
                # Record result in DB
                result_data = {
                    "task_id": task.id,
                    "model_name": model_name,
                    "category": task.category,
                    "success": success,
                    "syntax_correct": details.get("compile_success", success),
                    "compile_success": details.get("compile_success", success),
                    "test_success": details.get("test_success", success),
                    "tool_accuracy": details.get("tool_accuracy", 1.0 if success else 0.0),
                    "latency_ms": latency_ms,
                    "tokens_prompt": tokens_prompt,
                    "tokens_generated": tokens_gen,
                    "raw_output": raw_output
                }
                record_result(run_id, result_data)
                
                # Update model score in DB (EMA update)
                update_model_score(model_name, task.category, success, latency_ms, tokens_gen)
                
                status_str = "SUCCESS" if success else "FAILED"
                print(f" {status_str} ({latency_ms/1000:.2f}s, {tokens_gen} tokens)")
                if not success and "error" in details:
                    print(f"    Error details: {details['error']}")
                    
            except Exception as e:
                print(f" ERROR: {e}")
                # Record a failed result
                result_data = {
                    "task_id": task.id,
                    "model_name": model_name,
                    "category": task.category,
                    "success": False,
                    "syntax_correct": False,
                    "compile_success": False,
                    "test_success": False,
                    "tool_accuracy": 0.0,
                    "latency_ms": 0.0,
                    "tokens_prompt": 0,
                    "tokens_generated": 0,
                    "raw_output": f"Execution error: {str(e)}"
                }
                record_result(run_id, result_data)
                update_model_score(model_name, task.category, False, 5000.0, 0)
                
        print("-" * 60)
        
    print(f"Evaluation run {run_id} complete!")
    return run_id
