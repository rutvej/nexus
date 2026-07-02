from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, List, Dict, Any

class TaskStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    BLOCKED = "blocked"

@dataclass
class PlanStep:
    id: str
    description: str
    task_type: str                            # reasoning|code_generation|debugging|tool_calling|json_generation|planning
    tool_hint: Optional[str] = None
    tool_args_hint: Optional[Dict[str, Any]] = None
    dependencies: List[str] = field(default_factory=list)
    status: TaskStatus = TaskStatus.PENDING
    result: Optional[str] = None
    error: Optional[str] = None
    retries: int = 0
    max_retries: int = 2

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "description": self.description,
            "task_type": self.task_type,
            "tool_hint": self.tool_hint,
            "tool_args_hint": self.tool_args_hint,
            "dependencies": self.dependencies,
            "status": self.status.value,
            "result": self.result,
            "error": self.error,
            "retries": self.retries,
            "max_retries": self.max_retries
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PlanStep':
        step = cls(
            id=data["id"],
            description=data["description"],
            task_type=data["task_type"],
            tool_hint=data.get("tool_hint"),
            tool_args_hint=data.get("tool_args_hint"),
            dependencies=data.get("dependencies", []),
            status=TaskStatus(data.get("status", "pending")),
            result=data.get("result"),
            error=data.get("error"),
            retries=data.get("retries", 0),
            max_retries=data.get("max_retries", 2)
        )
        return step

@dataclass
class PlanDAG:
    goal: str
    steps: Dict[str, PlanStep] = field(default_factory=dict)
    revised_count: int = 0

    def ready_steps(self) -> List[PlanStep]:
        """Return steps whose dependencies are all COMPLETED."""
        ready = []
        for step in self.steps.values():
            if step.status != TaskStatus.PENDING:
                continue
            
            # Check dependencies
            deps_ok = True
            for dep_id in step.dependencies:
                dep_step = self.steps.get(dep_id)
                if not dep_step or dep_step.status != TaskStatus.COMPLETED:
                    deps_ok = False
                    break
            
            if deps_ok:
                ready.append(step)
        return ready

    def is_complete(self) -> bool:
        return all(s.status in (TaskStatus.COMPLETED, TaskStatus.SKIPPED) for s in self.steps.values())

    def is_failed(self) -> bool:
        return any(s.status == TaskStatus.FAILED for s in self.steps.values())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "goal": self.goal,
            "steps": {k: v.to_dict() for k, v in self.steps.items()},
            "revised_count": self.revised_count
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PlanDAG':
        dag = cls(
            goal=data["goal"],
            steps={k: PlanStep.from_dict(v) for k, v in data["steps"].items()},
            revised_count=data.get("revised_count", 0)
        )
        return dag
