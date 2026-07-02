import json
from typing import Dict, Any, List
from nexus.planner.dag import PlanDAG, PlanStep, TaskStatus
from nexus.models.router import ModelRouter

PLANNING_SYSTEM_PROMPT = """You are the Nexus Planner. Your job is to decompose a high-level user goal into a sequence of structured steps represented as a Directed Acyclic Graph (DAG).

You must respond with a JSON object containing a "steps" array. Each step must have:
- "id": A short unique identifier (e.g. "step1", "read_code", "write_fix").
- "description": A clear description of what this step does.
- "task_type": The type of task: "reasoning", "planning", "code_generation", "debugging", "tool_calling", "json_generation".
- "tool_hint": (Optional) The name of a tool that might be useful: "read_file", "write_file", "replace_text", "list_dir", "terminal_exec".
- "tool_args_hint": (Optional) A JSON object containing suggested arguments for the tool.
- "dependencies": A list of step IDs that MUST be completed before this step can run. If none, provide an empty list [].

Ensure there are no circular dependencies. Keep the plan under 6 steps.
"""

class Planner:
    def __init__(self, router: ModelRouter):
        self.router = router

    def create_plan(self, goal: str) -> PlanDAG:
        prompt = f"Decompose the following goal into an executable plan:\nGoal: {goal}"
        
        # Call the model in JSON mode
        res = self.router.generate(
            task_type="planning",
            prompt=prompt,
            system_prompt=PLANNING_SYSTEM_PROMPT,
            json_mode=True
        )
        
        try:
            data = json.loads(res["text"])
            steps_data = data.get("steps", [])
            
            steps = {}
            for s in steps_data:
                step_id = s["id"]
                step = PlanStep(
                    id=step_id,
                    description=s["description"],
                    task_type=s["task_type"],
                    tool_hint=s.get("tool_hint"),
                    tool_args_hint=s.get("tool_args_hint"),
                    dependencies=s.get("dependencies", []),
                    status=TaskStatus.PENDING
                )
                steps[step_id] = step
                
            return PlanDAG(goal=goal, steps=steps)
        except Exception as e:
            # Fallback plan if model output is invalid
            # (Matches mitigation in Section 7.11 of the spec)
            print(f"Warning: Failed to parse planner JSON ({e}). Creating fallback plan.")
            fallback_steps = {
                "step1": PlanStep(
                    id="step1",
                    description="Analyze the project and gather context",
                    task_type="reasoning",
                    dependencies=[]
                ),
                "step2": PlanStep(
                    id="step2",
                    description="Implement the requested changes",
                    task_type="code_generation",
                    dependencies=["step1"]
                ),
                "step3": PlanStep(
                    id="step3",
                    description="Verify the changes",
                    task_type="debugging",
                    dependencies=["step2"]
                )
            }
            return PlanDAG(goal=goal, steps=fallback_steps)

    def revise_plan(self, plan: PlanDAG, failed_step: PlanStep, error: str) -> PlanDAG:
        """Revise the plan after a step failure."""
        plan.revised_count += 1
        prompt = (
            f"The plan to achieve the goal '{plan.goal}' has failed at step '{failed_step.id}' "
            f"with error: '{error}'.\n"
            f"Here is the current plan state:\n{json.dumps(plan.to_dict(), indent=2)}\n"
            f"Please generate a revised list of remaining steps to achieve the goal. "
            f"Only include pending or new steps. Respond with a JSON object in the same format."
        )
        
        res = self.router.generate(
            task_type="planning",
            prompt=prompt,
            system_prompt=PLANNING_SYSTEM_PROMPT,
            json_mode=True
        )
        
        try:
            data = json.loads(res["text"])
            steps_data = data.get("steps", [])
            
            # Keep completed steps from the original plan
            new_steps = {k: v for k, v in plan.steps.items() if v.status == TaskStatus.COMPLETED}
            
            for s in steps_data:
                step_id = s["id"]
                if step_id in new_steps:
                    continue # Don't overwrite completed steps
                step = PlanStep(
                    id=step_id,
                    description=s["description"],
                    task_type=s["task_type"],
                    tool_hint=s.get("tool_hint"),
                    tool_args_hint=s.get("tool_args_hint"),
                    dependencies=s.get("dependencies", []),
                    status=TaskStatus.PENDING
                )
                new_steps[step_id] = step
                
            plan.steps = new_steps
            return plan
        except Exception as e:
            print(f"Warning: Failed to revise plan ({e}). Continuing with original steps.")
            # Reset the failed step so it can be retried or handled
            failed_step.status = TaskStatus.PENDING
            return plan
