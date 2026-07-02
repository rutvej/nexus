import json
from typing import Dict, Any, List, Optional
from nexus.config.config import Config
from nexus.models.router import ModelRouter
from nexus.planner.planner import Planner
from nexus.planner.dag import PlanDAG, PlanStep, TaskStatus
from nexus.tools.registry import ToolRegistry
from nexus.tools.executor import ToolExecutor
from nexus.memory.manager import MemoryManager
from nexus.rag.indexer import RepositoryIndexer
from nexus.rag.search import RAGSearch
from nexus.context.manager import ContextManager
from nexus.evaluation.evaluator import EvaluationEngine
from rich.console import Console

TOOL_CALLING_SYSTEM_PROMPT = """You are the Nexus Tool Caller. Based on the task description and available tools, choose the best tool and parameters.

Available tools:
{tool_descriptions}

You must respond with a JSON object in the exact format:
{{
  "tool": "tool_name",
  "args": {{
    "arg1": "val1"
  }}
}}
"""

class AgentCore:
    def __init__(self, config: Config, router: ModelRouter, registry: ToolRegistry, executor: ToolExecutor):
        self.config = config
        self.router = router
        self.registry = registry
        self.executor = executor
        self.planner = Planner(router)
        self.console = Console()
        self.max_steps = self.config.get("agent.max_steps", 15)
        
        # Initialize RAG, Memory, and Evaluation
        self.memory = MemoryManager()
        self.indexer = RepositoryIndexer()
        self.rag_search = RAGSearch(self.indexer)
        self.context_manager = ContextManager(self.memory, self.rag_search)
        self.evaluator = EvaluationEngine()

    def run(self, goal: str) -> Dict[str, Any]:
        self.console.print(f"\n[bold green]🚀 Initializing Nexus Agent[/bold green]")
        self.console.print(f"Goal: [italic]{goal}[/italic]")
        
        # Scan the repository for RAG
        self.console.print("[dim]Indexing workspace...[/dim]")
        self.indexer.scan()
        self.console.print(f"[dim]Indexed {len(self.indexer.files)} files and {len(self.indexer.get_all_symbols())} symbols.[/dim]")
        
        # 1. Create Plan
        self.console.print("[dim]Planning...[/dim]")
        plan = self.planner.create_plan(goal)
        self.console.print("\n[bold]Execution Plan:[/bold]")
        for step_id, step in plan.steps.items():
            self.console.print(f"  - [bold]{step_id}[/bold]: {step.description} ({step.task_type})")
        self.console.print("-" * 60)

        step_count = 0
        self.memory.clear_conversation()
        
        # 2. Execution Loop
        while not plan.is_complete() and not plan.is_failed() and step_count < self.max_steps:
            ready = plan.ready_steps()
            if not ready:
                if not plan.is_complete():
                    self.console.print("[red]Error: Plan deadlock. No steps are ready but goal is not complete.[/red]")
                    break
                
            for step in ready:
                step_count += 1
                self.console.print(f"\n[bold blue]▶ Step {step_count}: {step.description} ({step.task_type})[/bold blue]")
                step.status = TaskStatus.RUNNING
                
                # Assemble context (RAG + Memory)
                context = self.context_manager.assemble_context(goal, step.description)
                
                # Execute the step
                success, output, error, metrics = self._execute_step(step, plan.goal, context)
                
                if success:
                    step.status = TaskStatus.COMPLETED
                    step.result = output
                    self.console.print(f"[green]✓ Step {step.id} completed successfully.[/green]")
                    
                    # Log to conversation memory
                    self.memory.add_message("user", f"Step: {step.description}")
                    self.memory.add_message("assistant", f"Result: {output[:300]}...")
                    
                    # Evaluate if files were modified
                    if step.tool_hint in ("write_file", "replace_text") and step.tool_args_hint:
                        path = step.tool_args_hint.get("path")
                        if path:
                            self.console.print(f"[dim]Evaluating code quality for {path}...[/dim]")
                            eval_res = self.evaluator.evaluate_code(path)
                            if not eval_res["syntax_correct"]:
                                self.console.print(f"[yellow]Warning: Syntax error detected in {path}: {eval_res['error']}[/yellow]")
                                # Treat syntax error as step failure to trigger revision
                                success = False
                                error = f"Syntax error in {path}: {eval_res['error']}"
                                step.status = TaskStatus.FAILED
                                step.error = error
                                
                    # Feed back to scoring database (EMA update)
                    if metrics:
                        self.evaluator.process_feedback(
                            model_name=metrics["model"],
                            task_type=step.task_type,
                            success=success,
                            latency_ms=metrics["latency_ms"],
                            tokens_gen=metrics["tokens_generated"]
                        )
                
                if not success:
                    step.status = TaskStatus.FAILED
                    step.error = error
                    self.console.print(f"[red]✗ Step {step.id} failed: {error}[/red]")
                    
                    # Feed back failure to scoring database
                    if metrics:
                        self.evaluator.process_feedback(
                            model_name=metrics["model"],
                            task_type=step.task_type,
                            success=False,
                            latency_ms=metrics["latency_ms"],
                            tokens_gen=metrics["tokens_generated"]
                        )
                    
                    # Handle retry or revision
                    if step.retries < step.max_retries:
                        step.retries += 1
                        step.status = TaskStatus.PENDING
                        self.console.print(f"[yellow]Retrying step {step.id} (Attempt {step.retries}/{step.max_retries})...[/yellow]")
                    else:
                        self.console.print(f"[yellow]Revising plan after failure...[/yellow]")
                        plan = self.planner.revise_plan(plan, step, error)
                        break # Break out of ready steps to re-evaluate new plan

        # 3. Final Report
        self.console.print("\n" + "=" * 60)
        if plan.is_complete():
            self.console.print("[bold green]🎉 Goal Achieved successfully![/bold green]")
            return {"success": True, "steps_executed": step_count, "plan": plan}
        else:
            self.console.print("[bold red]❌ Goal Execution Failed.[/bold red]")
            return {"success": False, "steps_executed": step_count, "plan": plan}

    def _execute_step(self, step: PlanStep, goal: str, context: str) -> tuple[bool, str, Optional[str], Optional[Dict[str, Any]]]:
        """Execute a single step, returning (success, output, error, metrics)."""
        
        # If the step is a tool calling or file/exec task type, or has a tool_hint,
        # we ask the model to generate the tool call.
        if step.task_type in ("tool_calling", "code_generation", "debugging") or step.tool_hint:
            # 1. Ask the model to select and parameterize the tool
            prompt = (
                f"Goal: {goal}\n"
                f"Context:\n{context}\n\n"
                f"Current Step: {step.description}\n"
                f"Task Type: {step.task_type}\n"
            )
            if step.tool_hint:
                prompt += f"Suggested Tool: {step.tool_hint}\n"
                if step.tool_args_hint:
                    prompt += f"Suggested Arguments: {step.tool_args_hint}\n"
            
            # Format tool descriptions
            tool_desc = self.registry.get_tool_descriptions()
            sys_prompt = TOOL_CALLING_SYSTEM_PROMPT.format(tool_descriptions=tool_desc)
            
            try:
                # Route and generate
                model_name, host_url = self.router.route("tool_calling")
                res = self.router.generate(
                    task_type="tool_calling",
                    prompt=prompt,
                    system_prompt=sys_prompt,
                    json_mode=True
                )
                
                metrics = {
                    "model": model_name,
                    "latency_ms": res["latency_ms"],
                    "tokens_generated": res["tokens_generated"]
                }
                
                tool_data = json.loads(res["text"])
                tool_name = tool_data.get("tool")
                tool_args = tool_data.get("args", {})
                
                if not tool_name:
                    return False, "", "Model did not specify a tool to call.", metrics
                
                # Execute the tool
                self.console.print(f"[dim]Executing tool: {tool_name}({tool_args})[/dim]")
                result = self.executor.execute(tool_name, tool_args)
                
                if result.success:
                    return True, result.output, None, metrics
                else:
                    return False, "", result.error, metrics
            except Exception as e:
                return False, "", f"Failed to execute tool step: {str(e)}", None
                
        else:
            # For reasoning or planning steps that don't call tools, just use the model to reason/respond.
            prompt = f"Goal: {goal}\nContext:\n{context}\n\nStep: {step.description}\nPlease perform the task and return your final response."
            try:
                model_name, host_url = self.router.route(step.task_type)
                res = self.router.generate(
                    task_type=step.task_type,
                    prompt=prompt
                )
                metrics = {
                    "model": model_name,
                    "latency_ms": res["latency_ms"],
                    "tokens_generated": res["tokens_generated"]
                }
                self.console.print(res["text"])
                return True, res["text"], None, metrics
            except Exception as e:
                return False, "", str(e), None
