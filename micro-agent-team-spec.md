# Nexus — Micro-Agent Team Specification

This document defines the roles, workflows, verification loops, and state recovery mechanisms for the Nexus Hierarchical Micro-Agent Team.

---

## 1. Team Roles & Prompt Boundaries

To prevent cognitive overload on sub-3B models, the agentic loop is divided into three distinct roles:

```
┌────────────────────────────────────────────────────────┐
│                        MANAGER                         │
│  • Decomposes high-level goal into micro-tickets.      │
│  • Manages the Scrum Board & Shadow Git Branches.      │
└───────────────────────────┬────────────────────────────┘
                            │
                            ▼
┌────────────────────────────────────────────────────────┐
│                    SENIOR DEVELOPER                    │
│  • Writes unit tests (TDD) defining success criteria.  │
│  • Reviews code & tracebacks.                          │
└───────────────────────────┬────────────────────────────┘
                            │
                            ▼
┌────────────────────────────────────────────────────────┐
│                    JUNIOR DEVELOPER                    │
│  • Writes implementation code in the target file.       │
│  • Runs tests and refactors based on tracebacks.       │
└────────────────────────────────────────────────────────┘
```

---

## 2. Test-Driven Verification Loop (TDD)

To prevent "silent successes" and code hallucinations, all coding tasks must follow a strict **Test-First** loop.

### 2.1 Cheating Prevention (Property-Based Testing)
To prevent the Junior Developer from writing hardcoded returns (e.g. `return 5` for `assert add(2,3) == 5`), the Senior Developer is instructed to generate at least **3 distinct test cases** with randomized inputs or utilizing property-based assertions.

### 2.2 Pre-Flight Test Validation
Before the Junior Developer receives the test, the system runs a pre-flight compile check (`py_compile` and `ast.parse`) on the test file. If the test file itself contains syntax errors, it is rejected and sent back to the Senior Developer for regeneration, preventing infinite debugging loops on broken specifications.

---

## 3. Deterministic Static Analysis Gates

Before code is committed, it must pass a suite of deterministic static analysis tools. This bypasses LLM-sycophancy and guarantees code quality.

```python
import subprocess
from typing import Dict, Any

class StaticAnalysisGate:
    """Runs deterministic linters and security scanners on agent-generated code."""
    
    def __init__(self, file_path: str):
        self.file_path = file_path

    def run_all_checks(self) -> Dict[str, Any]:
        results = {
            "black_passed": False,
            "mypy_passed": False,
            "bandit_passed": False,
            "errors": []
        }
        
        # 1. Run Black (Style check)
        black_res = subprocess.run(["black", "--check", self.file_path], capture_output=True, text=True)
        results["black_passed"] = black_res.returncode == 0
        if black_res.returncode != 0:
            results["errors"].append(f"Black style check failed:\n{black_res.stderr}")
            
        # 2. Run Mypy (Type checker)
        mypy_res = subprocess.run(["mypy", self.file_path], capture_output=True, text=True)
        results["mypy_passed"] = mypy_res.returncode == 0
        if mypy_res.returncode != 0:
            results["errors"].append(f"Mypy type check failed:\n{mypy_res.stdout}")
            
        # 3. Run Bandit (Security scanner)
        bandit_res = subprocess.run(["bandit", "-r", self.file_path, "-f", "txt"], capture_output=True, text=True)
        results["bandit_passed"] = bandit_res.returncode == 0
        if bandit_res.returncode != 0:
            results["errors"].append(f"Bandit security vulnerabilities found:\n{bandit_res.stdout}")
            
        return results
```

---

## 4. Session Hydration & Write-Ahead Logging (WAL)

To recover from unexpected crashes (e.g. system restarts or power outages), the agent writes every state transition and plan update to a local SQLite database (`.nexus/session.db`) before executing any step.

```python
import sqlite3
import json
from typing import Optional, Dict, Any

class SessionHydrator:
    """Saves and restores agent session state from a local SQLite database."""
    
    def __init__(self, db_path: str = ".nexus/session.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS session_state (
                    session_id TEXT PRIMARY KEY,
                    current_step_id TEXT,
                    active_plan TEXT,
                    git_checkpoint TEXT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

    def save_state(self, session_id: str, step_id: str, plan: Dict[str, Any], git_hash: str):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO session_state (session_id, current_step_id, active_plan, git_checkpoint)
                VALUES (?, ?, ?, ?)
            """, (session_id, step_id, json.dumps(plan), git_hash))

    def load_state(self, session_id: str) -> Optional[Dict[str, Any]]:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT current_step_id, active_plan, git_checkpoint FROM session_state WHERE session_id = ?", (session_id,))
            row = cursor.fetchone()
            if row:
                return {
                    "current_step_id": row[0],
                    "active_plan": json.loads(row[1]),
                    "git_checkpoint": row[2]
                }
        return None
```

---

## 5. Persistent Project Guide (PROJECT_GUIDE.md)

### 5.1 Purpose
To prevent "Context Blindness" across multi-file tasks by maintaining a single, persistent Markdown file (`.nexus/PROJECT_GUIDE.md`) that serves as the agent's shared memory of the project's architecture, active schemas, and conventions.

### 5.2 Project Guide Structure
The `.nexus/PROJECT_GUIDE.md` is automatically created and updated by the **Manager** and injected into the context of all Senior and Junior developer prompts by the `ContextManager`.

```markdown
# Nexus Project Guide

## 1. Technology Stack
- Language: Python 3.12
- Database: SQLite
- Framework: FastAPI

## 2. Directory Structure
- `src/nexus/`: Core agent code.
- `tests/`: Unit and integration tests.

## 3. Active Schemas
### users table
- `id` (INTEGER, PK)
- `username` (TEXT, UNIQUE)
- `password_hash` (TEXT)

## 4. Architectural Conventions
- All database operations must utilize the `sqlite3` context manager.
- All new API endpoints must be defined in `src/nexus/cli/app.py`.
```

### 5.3 Automated Maintenance Workflow
1.  **Ticket Completion:** When a ticket is completed (e.g., "Create database schema"), the **Manager** parses the file diffs.
2.  **Update Guide:** The Manager updates the relevant sections of `.nexus/PROJECT_GUIDE.md` (e.g., appending the new database schema).
3.  **Prompt Injection:** For all subsequent tickets, the `ContextManager` reads this file and prefixes it to the prompt, ensuring the team is always aligned on the latest system state.

