# program.md — Nexus Agent Experiment Program

**Version:** 1.0  
**Author:** Opus 4.6 (Spec & Monitor)  
**Executor:** Gemini Flash 3.5 (Code & Build)  
**Date:** 2026-07-02  

---

## 0. How To Use This Document

You are an AI coding agent. This document is your **mission briefing**. Follow it section by section, in order. Do NOT skip ahead. After completing each phase, update the checkpoint file at `.nexus/checkpoint.md` before proceeding.

> [!IMPORTANT]
> **Read the full spec files before writing any code.**  
> - `chat-summary-spec.md` — Past failures and lessons learned  
> - `micro-agent-team-spec.md` — Team roles, TDD loop, session hydration  
> - `security-and-sandboxing-spec.md` — Sandbox tiers, process isolation  
> - `multi-model-agent-spec.md` — Full architecture reference  

---

## 1. Mission

Build the **Nexus coding agent**, run it inside Docker, instruct it to build a **Twitter clone**, monitor its behavior, fix its bugs, and iterate until the clone works. Then add a new feature to the clone to validate that the agent can extend existing projects.

### 1.1 Success Criteria

- [ ] Nexus agent runs inside Docker and connects to a local Ollama instance
- [ ] Nexus agent receives a task via its ticket system and produces working code
- [ ] Twitter clone has at minimum: user registration, login, create tweet, view timeline
- [ ] Agent successfully adds a new feature (e.g., "like" a tweet) to the existing clone
- [ ] All experiments are checkpointed — successes committed, failures logged and discarded
- [ ] CPU never sustains high load (all tasks are 1-story-point, one function at a time)

### 1.2 Roles

| Role | Who | Responsibilities |
|------|-----|-----------------|
| **Spec Writer & Monitor** | Opus 4.6 (separate conversation) | Write specs, review checkpoint.md, diagnose failures, suggest fixes |
| **Builder & Fixer** | Gemini Flash 3.5 (you, reading this) | Write code, run commands, apply fixes, update checkpoints |
| **Coding Worker** | Nexus Agent (sub-3B local model inside Docker) | Execute 1-story-point tickets: write functions, write tests |
| **Human Overseer** | Rutvej | Final authority, can override any decision |

---

## 2. Architecture Overview

### 2.1 The Ticket-As-Context Pattern

The core insight: **sub-3B models have tiny context windows (~2K-8K tokens), so we never ask them to think about the whole project.** Instead, every task is a self-contained ticket with exactly the context needed.

```
┌──────────────────────────────────────────────────────────┐
│  YOU (Gemini Flash — Builder Agent)                       │
│  • Builds the Nexus agent code                            │
│  • Runs Nexus inside Docker                               │
│  • Monitors Nexus output                                  │
│  • Fixes Nexus when it fails                              │
│  • Updates checkpoint.md                                  │
└──────────────┬───────────────────────────────────────────┘
               │ builds & monitors
               ▼
┌──────────────────────────────────────────────────────────┐
│  NEXUS AGENT (Python, runs inside Docker)                 │
│                                                           │
│  ┌─────────────┐     ┌─────────────┐     ┌────────────┐ │
│  │   MANAGER   │────▶│  TICKET     │────▶│  WORKER    │ │
│  │  (sub-3B)   │     │  QUEUE      │     │  (sub-3B)  │ │
│  │             │     │  (SQLite)   │     │            │ │
│  │ Decomposes  │     │             │     │ Writes ONE │ │
│  │ features    │     │ Stores all  │     │ function   │ │
│  │ into 1-SP   │     │ tickets +   │     │ or ONE     │ │
│  │ tickets     │     │ context     │     │ test per   │ │
│  └─────────────┘     └─────────────┘     │ ticket     │ │
│                                           └─────┬──────┘ │
│                                                 │        │
│  ┌─────────────┐     ┌─────────────┐           │        │
│  │  VERIFIER   │◀────│  RUNNER     │◀──────────┘        │
│  │(deterministic)    │  (pytest)   │                     │
│  │ black,mypy  │     │             │                     │
│  │ bandit,ast  │     │ Runs tests  │                     │
│  └──────┬──────┘     └─────────────┘                     │
│         │                                                 │
│    PASS │ FAIL                                            │
│    ┌────┴────┐                                            │
│    ▼         ▼                                            │
│  git       create                                         │
│  commit    debug                                          │
│            ticket                                         │
│            (max 3                                         │
│             retries                                       │
│             then                                          │
│             ESCALATE)                                     │
└──────────────────────────────────────────────────────────┘
               │
          ┌────┴────┐
          ▼         ▼
      Ollama     Docker
      (host)     Sandbox
      :11435     (no network)
```

### 2.2 Single Model, Multiple Prompts

**Use ONE sub-3B model for all roles.** Do NOT switch models between Manager and Worker. Differentiate roles by prompt template only. This prevents model thrashing and keeps CPU cool.

Recommended model: `qwen2.5-coder:1.5b` (best code generation at this size) or `gemma4:e2b` (if available, has native function calling).

### 2.3 The 1-Story-Point Rule

Every ticket must be completable with:
- **≤500 tokens of input context** (ticket description + relevant interfaces)
- **≤400 tokens of output** (one function body or one test function)
- **≤10 seconds of CPU inference time**

If a ticket requires more, it must be split further.

---

## 3. Build Plan — Phase by Phase

### Phase 1: Project Scaffolding

Create the Nexus agent as a minimal Python project inside `/home/rutvej/nexus/src/nexus/`.

#### 3.1.1 Files to Create

```
src/nexus/
├── __init__.py
├── __main__.py              # Entry point: python -m nexus
├── agent/
│   ├── __init__.py
│   ├── manager.py           # Decomposes features into tickets
│   ├── worker.py            # Executes one ticket (write code or test)
│   └── verifier.py          # Runs deterministic checks (black, mypy, pytest)
├── tickets/
│   ├── __init__.py
│   ├── models.py            # Ticket data model (dataclass)
│   ├── queue.py             # SQLite-backed ticket queue
│   ├── templates.py         # Ticket templates with mandatory fields
│   └── escalation.py        # Escalation logic (retry count, cloud fallback)
├── llm/
│   ├── __init__.py
│   ├── base.py              # Abstract LLM interface
│   ├── ollama_backend.py    # Ollama HTTP client (local sub-3B)
│   ├── cloud_stub.py        # Cloud API stubs (OpenAI, Anthropic, Google, DeepSeek)
│   └── router.py            # Try local → try cloud → escalate to human
├── project/
│   ├── __init__.py
│   ├── guide.py             # PROJECT_GUIDE.md reader/writer
│   ├── interface_registry.py # Tracks all function signatures
│   └── git_ops.py           # Git commit/rollback/checkpoint operations
├── sandbox/
│   ├── __init__.py
│   └── docker_runner.py     # Runs code inside Docker sandbox
└── config.py                # All configuration in one place
```

#### 3.1.2 Build Order

Build these files **in this exact order**. Each file should be testable independently.

| Step | File | Why This Order |
|------|------|---------------|
| 1 | `config.py` | Everything depends on config |
| 2 | `tickets/models.py` | Define the ticket data structure first |
| 3 | `tickets/queue.py` | Storage layer for tickets |
| 4 | `tickets/templates.py` | Ticket validation |
| 5 | `llm/base.py` | Abstract interface |
| 6 | `llm/ollama_backend.py` | Connect to local Ollama |
| 7 | `llm/cloud_stub.py` | Stub out cloud APIs (not functional yet) |
| 8 | `llm/router.py` | Route: local → cloud → human |
| 9 | `project/guide.py` | PROJECT_GUIDE.md management |
| 10 | `project/interface_registry.py` | Track function signatures |
| 11 | `project/git_ops.py` | Git checkpoint operations |
| 12 | `agent/verifier.py` | Deterministic checks (no LLM needed) |
| 13 | `agent/worker.py` | Executes tickets using LLM |
| 14 | `agent/manager.py` | Decomposes features into tickets |
| 15 | `tickets/escalation.py` | Handles failures and escalation |
| 16 | `sandbox/docker_runner.py` | Docker execution wrapper |
| 17 | `__main__.py` | Wire everything together |

#### 3.1.3 Testing Strategy

For each file, write a test file in `tests/` immediately after creating the source file. Run `pytest` after each test file to confirm it passes before moving on.

---

### Phase 2: Docker Environment

#### 3.2.1 Dockerfile for Nexus Agent

Create `docker/Dockerfile.nexus`:

```dockerfile
FROM python:3.12-slim

RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY pyproject.toml .
COPY src/ src/

RUN pip install -e .

# The agent writes code into /workspace (mounted volume)
VOLUME /workspace
WORKDIR /workspace

ENTRYPOINT ["python", "-m", "nexus"]
```

#### 3.2.2 Docker Compose for Full Stack

Create `docker/docker-compose.yml`:

```yaml
version: "3.8"
services:
  nexus-agent:
    build:
      context: ..
      dockerfile: docker/Dockerfile.nexus
    volumes:
      - nexus-workspace:/workspace
      - ../data:/data
    environment:
      - OLLAMA_HOST=http://host.docker.internal:11435
      - NEXUS_DATA_DIR=/data
    extra_hosts:
      - "host.docker.internal:host-gateway"

  nexus-sandbox:
    image: python:3.12-slim
    network_mode: none
    mem_limit: 512m
    cpus: 1
    volumes:
      - nexus-workspace:/workspace:ro
      - nexus-sandbox-work:/sandbox
    working_dir: /sandbox
    profiles: ["sandbox"]

volumes:
  nexus-workspace:
  nexus-sandbox-work:
```

---

### Phase 3: The Ticket System (Minimal Jira)

This is the heart of the system. Keep it minimal — SQLite + dataclasses, no frameworks.

#### 3.3.1 Ticket Data Model

```python
# tickets/models.py
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional
import datetime

class TicketStatus(Enum):
    BACKLOG = "backlog"
    IN_PROGRESS = "in_progress"
    TESTING = "testing"
    DONE = "done"
    FAILED = "failed"
    ESCALATED = "escalated"

class TicketType(Enum):
    CREATE_FILE = "create_file"
    WRITE_FUNCTION = "write_function"
    WRITE_TEST = "write_test"
    RUN_TESTS = "run_tests"
    FIX_BUG = "fix_bug"
    INTEGRATION_TEST = "integration_test"

@dataclass
class Ticket:
    id: str                                    # e.g., "TWIT-001"
    type: TicketType
    title: str                                 # e.g., "Write function create_user"
    status: TicketStatus = TicketStatus.BACKLOG
    
    # === MANDATORY CONTEXT (this IS the model's context window) ===
    target_file: str = ""                      # e.g., "src/models/user.py"
    function_signature: str = ""               # e.g., "def create_user(username: str, password: str) -> dict"
    parameters: str = ""                       # e.g., "username: str, password: str"
    return_type: str = ""                      # e.g., "dict with keys: id, username, password_hash"
    dependencies: str = ""                     # e.g., "import sqlite3, import hashlib"
    related_interfaces: str = ""               # Signatures of functions this depends on
    description: str = ""                      # What the function should do (1-2 sentences)
    
    # === EXECUTION STATE ===
    retry_count: int = 0
    max_retries: int = 3
    error_log: str = ""
    llm_output: str = ""
    git_hash_before: str = ""
    git_hash_after: str = ""
    
    # === DEPENDENCIES ===
    depends_on: list[str] = field(default_factory=list)
    blocks: list[str] = field(default_factory=list)
    epic: str = ""
    
    # === TIMESTAMPS ===
    created_at: str = field(default_factory=lambda: datetime.datetime.now().isoformat())
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    
    # === ESCALATION ===
    escalation_note: str = ""
    human_feedback: str = ""
```

#### 3.3.2 Key Invariant

> **The ticket's context fields (target_file, function_signature, parameters, return_type, dependencies, related_interfaces, description) must total ≤500 tokens when rendered into a prompt.** If they exceed this, the ticket must be split.

---

### Phase 4: The LLM Interface

#### 3.4.1 Routing Priority

```
1. LOCAL (Ollama sub-3B)  →  always try first
2. CLOUD (API stubs)      →  only if local fails 3 times AND cloud is configured
3. HUMAN (ticket escalation) → if both local and cloud fail
```

#### 3.4.2 Cloud API Stubs

Create stubs for ALL major providers. Each stub should:
- Accept the same interface as the Ollama backend
- Raise `NotConfiguredError` if no API key is set
- Be ready to activate with just an API key in config

Providers to stub:
- **OpenAI** (GPT-4o-mini, GPT-5.4-nano)
- **Anthropic** (Claude Haiku 4.5, Claude Sonnet 4.6)
- **Google** (Gemini Flash-Lite, Gemini Flash)
- **DeepSeek** (V4-Flash)
- **Ollama Cloud** (if user has remote Ollama)

#### 3.4.3 Prompt Templates

Each ticket type has a strict prompt template. The model receives ONLY this — no chat history, no system prompt bloat.

```
WRITE_FUNCTION prompt template:

Write a Python function with this exact signature:

{function_signature}

Parameters:
{parameters}

Returns:
{return_type}

Dependencies (already imported):
{dependencies}

The function should:
{description}

Related interfaces you may call:
{related_interfaces}

Write ONLY the function body. Do not write imports, do not write tests, 
do not write comments outside the function.
```

> [!CAUTION]
> **The prompt must NEVER include the full file contents.** Only the function signature and relevant interfaces. This keeps context under 500 tokens.

---

### Phase 5: The Verification Pipeline

All verification is **deterministic** — no LLM involved.

```
Agent writes code
       │
       ▼
┌──────────────┐
│ ast.parse()  │──FAIL──▶ Create FIX_BUG ticket with SyntaxError
│ (syntax ok?) │
└──────┬───────┘
       │ PASS
       ▼
┌──────────────┐
│ black --check│──FAIL──▶ Auto-fix with black (no ticket needed)
│ (formatted?) │
└──────┬───────┘
       │ PASS
       ▼
┌──────────────┐
│ pytest -x    │──FAIL──▶ Create FIX_BUG ticket with traceback
│ (tests pass?)│          (attach full traceback as context)
└──────┬───────┘
       │ PASS
       ▼
   git commit
   update PROJECT_GUIDE.md
   update interface_registry
   mark ticket DONE
```

---

### Phase 6: The Checkpoint System

#### 3.6.1 Nexus Agent Checkpoints (inside Docker)

The Nexus agent maintains its own state in `.nexus/session.db` (SQLite):

```sql
CREATE TABLE checkpoints (
    checkpoint_id TEXT PRIMARY KEY,
    ticket_id TEXT,
    git_hash TEXT,
    status TEXT,           -- 'success' | 'failure' | 'escalated'
    timestamp TEXT,
    error_log TEXT,
    files_changed TEXT     -- JSON list of file paths
);
```

On success: `git commit -m "TICKET-XXX: {title}"`  
On failure: `git stash` or `git checkout .` to discard changes, log the failure.

#### 3.6.2 Builder Agent Checkpoints (you, Gemini Flash)

You (the agent reading this) must maintain a checkpoint file at `.nexus/checkpoint.md`:

```markdown
# Builder Checkpoint

## Current Phase: [Phase number]
## Current Step: [Step number]
## Last Successful Action: [description]
## Nexus Agent Status: [running | stopped | crashed]

## Experiment Log

| Timestamp | Action | Result | Notes |
|-----------|--------|--------|-------|
| ... | Built config.py | PASS | |
| ... | Built ticket models | PASS | |

## Agent Modifications Log

| Timestamp | File Changed | What Was Wrong | Fix Applied |
|-----------|-------------|----------------|-------------|

## Known Issues (Unresolved)

- [ ] Issue description...
```

> [!IMPORTANT]
> **Update checkpoint.md after EVERY significant action.** This is how the Monitor (Opus 4.6) tracks your progress and diagnoses issues.

---

### Phase 7: The Experiment Protocol

Once the Nexus agent is built:

#### Step 1: First Run — Scaffold the Twitter Clone

Give the Nexus agent this prompt:

```
Create a Python web application called "tweeter" using Flask.
The app needs:
1. User registration (username + password)
2. User login with session management
3. Create a tweet (text only, max 280 chars)
4. View timeline (all tweets, newest first)

Use SQLite for the database. Keep it simple.
```

#### Step 2: Monitor the Ticket Queue

Watch the Nexus agent's ticket queue. Check:
- [ ] Did the Manager decompose this into reasonable 1-SP tickets?
- [ ] Are the tickets in the right dependency order?
- [ ] Does each ticket have all mandatory fields filled?

If the Manager produced bad tickets → **this is an agent bug**. Fix `agent/manager.py` prompt template.

#### Step 3: Watch Ticket Execution

For each ticket the Worker executes:
- [ ] Did the LLM produce valid Python?
- [ ] Did it pass `ast.parse()`?
- [ ] Did the tests pass?

Common failure patterns and responses:

| Failure Pattern | Is It Agent Bug or Ticket Feedback? | Action |
|----------------|-------------------------------------|--------|
| LLM outputs markdown/explanation instead of code | **Agent bug** | Fix Worker prompt: add "Output ONLY Python code" |
| Function has wrong signature | **Agent bug** | Fix Manager: ensure signature is in ticket |
| Function works but doesn't match interface | **Ticket feedback** | Create new ticket with correct interface context |
| Import error (module not found) | **Ticket feedback** | Add missing dependency to ticket context |
| Test fails on edge case | **Ticket feedback** | Create FIX_BUG ticket with traceback |
| Model outputs empty/garbage | **Agent bug** | Check Ollama connection, check prompt size |
| Infinite retry loop | **Agent bug** | Fix escalation.py: ensure retry_count increments |

#### Step 4: The Decision Framework

When something fails, use this decision tree:

```
Ticket failed
    │
    ├── Is the error in the AGENT code (not the generated code)?
    │   YES → Fix the agent code, restart from checkpoint
    │   NO  ↓
    │
    ├── Has this ticket failed < 3 times?
    │   YES → Create FIX_BUG ticket with traceback context
    │   NO  ↓
    │
    ├── Is cloud LLM configured?
    │   YES → Escalate to cloud model (try once)
    │   NO  ↓
    │
    └── ESCALATE to human (write escalation note in ticket)
        YOU (Gemini Flash) are the human for this experiment.
        Read the escalation note.
        Decide: can you provide feedback that fixes it?
          YES → Write human_feedback on the ticket, retry
          NO  → Modify the agent code to handle this case
```

#### Step 5: Feature Extension Test

Once the base Twitter clone works, give the Nexus agent:

```
Add a "like" feature to the tweeter app:
1. Users can like/unlike a tweet
2. Each tweet shows its like count
3. A user can only like a tweet once
```

This tests:
- Can the Manager read the existing PROJECT_GUIDE.md and produce tickets that integrate with existing code?
- Can the Worker modify existing files (not just create new ones)?
- Does the interface registry help avoid integration bugs?

---

## 4. Interface Registry Specification

The interface registry is a section of `.nexus/PROJECT_GUIDE.md` that tracks every function the agent has written. The Manager MUST read this before creating new tickets.

Format:
```markdown
## Interface Registry

### src/models/user.py
- `create_user(username: str, password: str) -> dict` — Returns {"id": int, "username": str, "password_hash": str}
- `get_user_by_username(username: str) -> Optional[dict]` — Returns user dict or None

### src/models/tweet.py
- `create_tweet(user_id: int, content: str) -> dict` — Returns {"id": int, "user_id": int, "content": str, "created_at": str}
```

This is small (~50-100 tokens per module) and fits easily in the Manager's context window.

---

## 5. Loop Detection & Prevention

### 5.1 How Loops Happen

From chat-summary-spec.md: *"When a sub-3B model generates a broken test, the implementing model gets trapped in an infinite loop trying to satisfy impossible assertions."*

### 5.2 Loop Detection Rules

```python
MAX_RETRIES_PER_TICKET = 3
MAX_CONSECUTIVE_FAILURES = 5    # across all tickets
MAX_IDENTICAL_OUTPUTS = 2       # if LLM produces same output twice, it's stuck

def is_stuck(ticket, history):
    if ticket.retry_count >= MAX_RETRIES_PER_TICKET:
        return True, "max_retries_exceeded"
    
    recent = history[-MAX_CONSECUTIVE_FAILURES:]
    if all(t.status == TicketStatus.FAILED for t in recent):
        return True, "consecutive_failure_streak"
    
    if ticket.retry_count >= 2:
        outputs = get_previous_outputs(ticket.id)
        if len(set(outputs)) < len(outputs):
            return True, "identical_output_loop"
    
    return False, None
```

### 5.3 What To Do When Stuck

1. **STOP the current ticket** — do not retry again
2. **Log everything** — the ticket context, all LLM outputs, all tracebacks
3. **Mark ticket as ESCALATED**
4. **Move to the next independent ticket** — don't block the whole queue
5. **Write an escalation note** summarizing what was tried

---

## 6. Cloud LLM Integration (Stubs)

### 6.1 Unified Interface

```python
# llm/base.py
from abc import ABC, abstractmethod
from dataclasses import dataclass

@dataclass
class LLMResponse:
    text: str
    model: str
    tokens_used: int
    latency_ms: float
    success: bool
    error: str = ""

class BaseLLM(ABC):
    @abstractmethod
    def generate(self, prompt: str, max_tokens: int = 400) -> LLMResponse:
        ...
    
    @abstractmethod
    def is_available(self) -> bool:
        ...
    
    @abstractmethod
    def name(self) -> str:
        ...
```

### 6.2 Providers to Stub

Each stub follows this pattern — accept same interface, raise NotConfiguredError if no API key:
- **OpenAI** (GPT-4o-mini, GPT-5.4-nano)
- **Anthropic** (Claude Haiku 4.5, Claude Sonnet 4.6)
- **Google** (Gemini Flash-Lite, Gemini Flash)
- **DeepSeek** (V4-Flash)

---

## 7. Safety Rules

### 7.1 Docker Isolation

- The Nexus agent runs inside Docker
- Generated code runs inside a **nested sandbox** (`--network=none`)
- The agent container CAN access Ollama on the host
- The sandbox container CANNOT access the network

### 7.2 Git Safety

- **NEVER force push**
- **NEVER commit to main/master** — use branch `nexus/experiment-001`
- Every commit message includes the ticket ID
- Before destructive operations, create a git tag: `checkpoint-{timestamp}`

### 7.3 Resource Limits

- Ollama inference timeout: 30 seconds per call
- pytest timeout: 60 seconds per test suite
- Total experiment budget: 500 tickets (hard stop)

---

## 8. Experiment Termination Conditions

Stop the experiment when ANY of these are true:

- [ ] **Success:** Twitter clone passes all integration tests AND feature extension works
- [ ] **Budget exceeded:** 500+ tickets processed
- [ ] **Stuck:** 10+ consecutive escalated tickets with no resolution
- [ ] **Human override:** User says stop
- [ ] **Infrastructure failure:** Docker/Ollama down and unrecoverable

Write final results to `.nexus/experiment-report.md` regardless of outcome.

---

## 9. Startup Sequence (for Gemini Flash)

```
1. Read all spec files (Section 0)
2. Create .nexus/checkpoint.md
3. Build Phase 1 files (one at a time, test each)
4. Build Phase 2 Docker files
5. Verify Ollama is accessible on host:11435
6. Verify a sub-3B model is loaded (pull one if not)
7. Build and start the Docker container
8. Run the experiment (Phase 7)
9. Monitor and fix (Phase 7, Steps 2-4)
10. Run feature extension test (Phase 7, Step 5)
11. Write final report to .nexus/experiment-report.md
```

---

## 10. Known Issues To Watch For

| # | Issue | Detection | Response |
|---|-------|-----------|----------|
| 1 | Manager produces tickets without function signatures | Ticket missing `function_signature` field | Fix Manager prompt template |
| 2 | Worker outputs markdown instead of Python | Output starts with ``` or contains natural language | Add "Output ONLY executable Python" to prompt |
| 3 | Worker ignores return type specification | Function returns wrong type | Add return type assertion to test template |
| 4 | Model thrashes (loads/unloads repeatedly) | High latency, fan noise | Ensure only ONE model is used, pin with `keep_alive` |
| 5 | SQLite locking errors | "database is locked" in logs | Use WAL mode, single-writer pattern |
| 6 | Git merge conflicts on PROJECT_GUIDE.md | Conflict markers in file | Always read-then-write, never concurrent updates |
| 7 | pytest hangs on input() or server code | pytest doesn't return within 60s | Use `--timeout=60` flag, kill process group |
| 8 | Docker container can't reach Ollama | Connection refused on :11435 | Use `host.docker.internal` or `--network=host` |
| 9 | Ticket context exceeds 500 tokens | Slow/degraded model output | Split ticket, reduce `related_interfaces` |
| 10 | Agent builds code that imports non-stdlib packages | ImportError at runtime | Ticket must specify allowed imports; sandbox has no pip |
