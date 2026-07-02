# program.md — Nexus Agent: Build Specification

**Version:** 2.0  
**Author:** Opus 4.6 (Spec & Monitor)  
**Executor:** Gemini Flash 3.5 (Code & Build)  
**Date:** 2026-07-02  

---

## 0. How To Use This Document

You are an AI coding agent (Gemini Flash). This document is your **mission briefing**.

> [!CAUTION]
> **Read this distinction carefully — it is the most important thing in this document:**
>
> **Nexus** = A general-purpose coding agent that can build ANY project. It knows nothing about Twitter, to-do apps, or any specific application. It receives a natural language spec, breaks it into tickets, and writes code one function at a time using sub-3B local LLMs.
>
> **The Experiment** = After building Nexus, we TEST it by asking it to build a Twitter clone. But Nexus itself has ZERO Twitter-specific code. If we asked it to build a calculator or a blog, it should work the same way.

**Your job:** Build the Nexus agent. The agent must be project-agnostic.

> [!IMPORTANT]
> **Read the existing spec files before writing any code.** They contain lessons from previous failed attempts:
> - `chat-summary-spec.md` — Past failures and why sub-3B models struggle
> - `micro-agent-team-spec.md` — Team roles, TDD loop, session hydration
> - `security-and-sandboxing-spec.md` — Sandbox tiers, process isolation
> - `multi-model-agent-spec.md` — Full architecture reference (5000+ lines)

---

## 1. What Nexus IS

Nexus is a **general-purpose autonomous coding agent** that:

1. **Receives** a natural language project description from a user (e.g., "Build a Flask blog with auth")
2. **Decomposes** it into an ordered list of 1-story-point micro-tickets
3. **Executes** each ticket by asking a sub-3B local LLM to write ONE function or ONE test
4. **Verifies** each output with deterministic tools (ast.parse, black, pytest) — no LLM-based review
5. **Commits** successes to git, discards failures, logs everything
6. **Escalates** when stuck: first to cloud LLM (if configured), then to the human user via ticket
7. **Resumes** from checkpoints after crashes, fixes, or user feedback

### 1.1 What Nexus is NOT

- NOT a Twitter app builder (Twitter is just one test case)
- NOT a single-purpose script (it must handle any Python project)
- NOT dependent on cloud APIs (local-first, cloud is optional fallback)
- NOT a chatbot (it reads a spec, produces code, reports via tickets)

### 1.2 The Escalation Chain

```
User gives project spec
        │
        ▼
┌─────────────────┐
│  NEXUS MANAGER   │  Breaks spec into 1-SP tickets
│  (sub-3B local)  │  using ticket templates
└────────┬────────┘
         │
         ▼
┌─────────────────┐     ┌──────────────────┐
│  NEXUS WORKER    │────▶│  VERIFIER         │
│  (sub-3B local)  │     │  (deterministic)  │
│                  │     │  ast, black,      │
│  Writes 1 func   │     │  pytest           │
│  or 1 test       │     └────────┬─────────┘
└─────────────────┘              │
                            PASS │ FAIL
                          ┌──────┴──────┐
                          ▼             ▼
                     git commit    Retry (max 3)
                     next ticket        │
                                   Still failing?
                                        │
                                   ┌────▼────┐
                                   │ CLOUD   │  Ask a bigger model
                                   │ LLM     │  (if API key configured)
                                   │(optional)│
                                   └────┬────┘
                                   Still failing?
                                        │
                                   ┌────▼────┐
                                   │ HUMAN   │  Write escalation note
                                   │ (ticket)│  Wait for user feedback
                                   └─────────┘
```

### 1.3 Success Criteria (for the agent itself, not any specific project)

- [ ] Nexus can receive ANY natural language project description
- [ ] Nexus decomposes it into valid, ordered, 1-story-point tickets
- [ ] Each ticket has all mandatory fields (file path, function signature, params, return type, dependencies)
- [ ] Worker produces valid Python for each ticket
- [ ] Verifier catches bad code deterministically (no LLM review)
- [ ] Successes are git-committed, failures are discarded and logged
- [ ] Cloud LLM stubs are ready (not functional without API keys, but code is there)
- [ ] Escalation to human works (ticket marked ESCALATED with context)
- [ ] Agent resumes from checkpoints after restart
- [ ] CPU never heats up (one small inference at a time, ≤10 seconds per call)

---

## 2. Architecture

### 2.1 The Ticket-As-Context Pattern

Sub-3B models have tiny context windows (~2K-8K tokens). We NEVER ask them to think about the whole project. Every task is a self-contained ticket with exactly the context needed for ONE function or ONE test.

### 2.2 Single Model, Multiple Prompts

Use **ONE sub-3B model** for all roles (Manager and Worker). Differentiate by prompt template only. This prevents model thrashing and keeps CPU cool.

Recommended: `qwen2.5-coder:1.5b` or `gemma4:e2b` (if available).

### 2.3 The 1-Story-Point Rule

Every ticket must be completable with:
- **≤500 tokens of input context** (ticket description + relevant interfaces)
- **≤400 tokens of output** (one function body or one test function)
- **≤10 seconds of CPU inference time**

If a ticket requires more, it MUST be split further.

### 2.4 Context Management via Tickets + Interface Registry

Instead of RAG or embedding-based retrieval, Nexus uses two simple mechanisms:

1. **Ticket context fields** — each ticket carries exactly what the model needs (function signature, params, return type, dependencies, related interfaces)
2. **Interface Registry** — a section of `PROJECT_GUIDE.md` listing every function signature the agent has written. The Manager reads this before creating new tickets.

The Interface Registry format:
```markdown
## Interface Registry

### src/models/user.py
- `create_user(username: str, password: str) -> dict` — Returns {"id": int, "username": str, "password_hash": str}
- `get_user_by_username(username: str) -> Optional[dict]` — Returns user dict or None
```

This is ~50-100 tokens per module and fits in the Manager's context alongside the feature request.

---

## 3. Project Structure

### 3.1 Files to Create

```
src/nexus/
├── __init__.py
├── __main__.py              # Entry point: python -m nexus "Build a blog app"
├── config.py                # All configuration in one place
│
├── agent/
│   ├── __init__.py
│   ├── manager.py           # Receives project spec → creates tickets
│   │                        # Reads PROJECT_GUIDE.md + interface registry
│   │                        # Produces 1-SP tickets with all mandatory fields
│   │                        # PROJECT-AGNOSTIC — no hardcoded app knowledge
│   │
│   ├── worker.py            # Picks next ticket from queue → asks LLM → writes code
│   │                        # Handles WRITE_FUNCTION, WRITE_TEST, FIX_BUG tickets
│   │                        # Extracts code from LLM output (strips markdown, etc.)
│   │
│   └── verifier.py          # Runs deterministic checks on worker output
│                             # ast.parse → black → pytest
│                             # NO LLM involvement — pure tooling
│
├── tickets/
│   ├── __init__.py
│   ├── models.py            # Ticket dataclass, TicketStatus enum, TicketType enum
│   ├── queue.py             # SQLite-backed FIFO queue with dependency ordering
│   ├── templates.py         # Prompt templates per ticket type (WRITE_FUNCTION, etc.)
│   │                        # Mandatory field validation
│   └── escalation.py        # Retry counting, loop detection, escalation logic
│                             # local → cloud → human decision tree
│
├── llm/
│   ├── __init__.py
│   ├── base.py              # Abstract BaseLLM interface (generate, is_available, name)
│   ├── ollama_backend.py    # Ollama HTTP client for local sub-3B models
│   │                        # Connects to OLLAMA_HOST (default localhost:11434)
│   │                        # Timeout: 30 seconds per call
│   │
│   ├── cloud/               # Cloud API stubs — ALL major providers
│   │   ├── __init__.py
│   │   ├── openai_backend.py     # GPT-4o-mini, GPT-5.4-nano
│   │   ├── anthropic_backend.py  # Claude Haiku 4.5, Claude Sonnet 4.6
│   │   ├── google_backend.py     # Gemini Flash-Lite, Gemini Flash
│   │   └── deepseek_backend.py   # DeepSeek V4-Flash
│   │
│   └── router.py            # Tries local first → cloud if local fails 3x → human
│                             # Respects config flags (cloud_enabled, etc.)
│
├── project/
│   ├── __init__.py
│   ├── guide.py             # Reads/writes PROJECT_GUIDE.md for any project
│   │                        # Maintains: tech stack, directory structure, schemas
│   ├── interface_registry.py # Reads/writes the interface registry section
│   │                        # Tracks: file path → list of function signatures
│   └── git_ops.py           # git init, commit, tag, reset, stash
│                             # Branch: nexus/run-{timestamp}
│                             # Commit message: "TICKET-XXX: {title}"
│
├── sandbox/
│   ├── __init__.py
│   └── runner.py            # Runs pytest and code in isolated subprocess
│                             # Process group isolation (os.setsid)
│                             # Timeout: 60 seconds
│                             # Optional: Docker sandbox for untrusted code
│
└── loop/
    ├── __init__.py
    └── engine.py            # The main loop that ties everything together:
                              # 1. Manager creates tickets from spec
                              # 2. Pick next ticket (respecting dependencies)
                              # 3. Worker executes ticket
                              # 4. Verifier checks output
                              # 5. On pass: commit, update guide, next ticket
                              # 6. On fail: retry or escalate
                              # 7. Repeat until all tickets done or budget exceeded
```

### 3.2 Build Order

Build in this exact order. Each file must be testable independently.

| Step | File | Test File | Why This Order |
|------|------|-----------|---------------|
| 1 | `config.py` | `tests/test_config.py` | Everything depends on config |
| 2 | `tickets/models.py` | `tests/test_ticket_models.py` | Data structures first |
| 3 | `tickets/queue.py` | `tests/test_ticket_queue.py` | Storage layer |
| 4 | `tickets/templates.py` | `tests/test_templates.py` | Prompt rendering + validation |
| 5 | `tickets/escalation.py` | `tests/test_escalation.py` | Retry + loop detection logic |
| 6 | `llm/base.py` | `tests/test_llm_base.py` | Abstract interface |
| 7 | `llm/ollama_backend.py` | `tests/test_ollama.py` | Local LLM connection |
| 8 | `llm/cloud/*.py` | `tests/test_cloud_stubs.py` | All cloud stubs (one test file) |
| 9 | `llm/router.py` | `tests/test_router.py` | Routing logic |
| 10 | `project/guide.py` | `tests/test_guide.py` | PROJECT_GUIDE.md management |
| 11 | `project/interface_registry.py` | `tests/test_interface_registry.py` | Signature tracking |
| 12 | `project/git_ops.py` | `tests/test_git_ops.py` | Git operations |
| 13 | `sandbox/runner.py` | `tests/test_sandbox.py` | Isolated execution |
| 14 | `agent/verifier.py` | `tests/test_verifier.py` | Deterministic checks |
| 15 | `agent/worker.py` | `tests/test_worker.py` | Ticket execution |
| 16 | `agent/manager.py` | `tests/test_manager.py` | Spec decomposition |
| 17 | `loop/engine.py` | `tests/test_engine.py` | Main orchestration loop |
| 18 | `__main__.py` | — | CLI entry point |

### 3.3 Testing Rules

- Use `unittest.mock` to mock LLM calls — tests must pass WITHOUT Ollama running
- Test ticket queue with in-memory SQLite (`:memory:`)
- Test git_ops with `tempfile.TemporaryDirectory()` + `git init`
- Cloud stubs must test that `is_available()` returns `False` when no API key is set
- Router must test the full chain: local → cloud → human escalation

---

## 4. Key Component Specifications

### 4.1 Ticket Data Model

```python
class TicketStatus(Enum):
    BACKLOG = "backlog"
    IN_PROGRESS = "in_progress"
    TESTING = "testing"
    DONE = "done"
    FAILED = "failed"
    ESCALATED = "escalated"     # Waiting for human/cloud input

class TicketType(Enum):
    CREATE_FILE = "create_file"
    WRITE_FUNCTION = "write_function"
    WRITE_TEST = "write_test"
    RUN_TESTS = "run_tests"
    FIX_BUG = "fix_bug"
    INTEGRATION_TEST = "integration_test"

@dataclass
class Ticket:
    id: str                        # "PRJ-001" (auto-generated)
    type: TicketType
    title: str                     # "Write function create_user"
    status: TicketStatus

    # MANDATORY CONTEXT — this IS the model's context window
    target_file: str               # "src/models/user.py"
    function_signature: str        # "def create_user(username: str, password: str) -> dict"
    parameters: str                # "username: str, password: str"
    return_type: str               # "dict with keys: id, username, password_hash"
    dependencies: str              # "import sqlite3, import hashlib"
    related_interfaces: str        # Other function signatures this depends on
    description: str               # "Hash the password and insert into users table"

    # EXECUTION STATE
    retry_count: int = 0
    max_retries: int = 3
    error_log: str = ""
    llm_output: str = ""
    git_hash_before: str = ""
    git_hash_after: str = ""

    # DEPENDENCIES
    depends_on: list[str]          # Ticket IDs that must complete first
    blocks: list[str]              # Ticket IDs blocked by this
    epic: str                      # Parent feature name

    # ESCALATION
    escalation_note: str = ""      # Context for human/cloud
    human_feedback: str = ""       # Response from human/cloud
```

### 4.2 Prompt Templates (project-agnostic)

```python
WRITE_FUNCTION_PROMPT = """Write a Python function with this exact signature:

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

Write ONLY the function body. No imports, no tests, no comments outside the function."""


WRITE_TEST_PROMPT = """Write a pytest test function for:

{function_signature}

The function:
{description}

Expected return type:
{return_type}

Write exactly ONE test function. Include at least 3 assertions with different inputs.
Import the function from {target_file}.
Write ONLY the test function. No imports beyond pytest and the target function."""


FIX_BUG_PROMPT = """Fix this Python function. The test failed with this error:

Function:
{function_signature}

Error traceback:
{error_log}

The function should:
{description}

Write ONLY the corrected function body. No imports, no tests."""
```

> [!CAUTION]
> These templates are PROJECT-AGNOSTIC. They work for any Python project. The ticket's context fields carry the project-specific information.

### 4.3 Loop Detection

```python
MAX_RETRIES_PER_TICKET = 3
MAX_CONSECUTIVE_FAILURES = 5
MAX_IDENTICAL_OUTPUTS = 2

def is_stuck(ticket, history):
    # Rule 1: ticket retried too many times
    if ticket.retry_count >= MAX_RETRIES_PER_TICKET:
        return True, "max_retries_exceeded"

    # Rule 2: too many failures in a row across all tickets
    recent = [t for t in history[-MAX_CONSECUTIVE_FAILURES:]]
    if len(recent) == MAX_CONSECUTIVE_FAILURES and all(
        t.status == TicketStatus.FAILED for t in recent
    ):
        return True, "consecutive_failure_streak"

    # Rule 3: model producing identical output
    if ticket.retry_count >= 2:
        outputs = get_previous_outputs(ticket.id)
        if len(set(outputs)) < len(outputs):
            return True, "identical_output_loop"

    return False, None
```

### 4.4 The Main Loop (loop/engine.py)

```python
def run(project_spec: str, config: Config):
    """
    The main Nexus loop. Project-agnostic.

    1. Manager reads spec → creates tickets
    2. Loop: pick next ticket → worker executes → verifier checks
    3. On pass: commit, update guide/registry, mark DONE
    4. On fail: retry or escalate
    5. Stop when: all done, budget exceeded, or stuck
    """
    manager = Manager(config)
    worker = Worker(config)
    verifier = Verifier(config)
    queue = TicketQueue(config.db_path)
    git = GitOps(config.workspace)
    guide = ProjectGuide(config.workspace)
    registry = InterfaceRegistry(config.workspace)
    escalation = EscalationHandler(config)

    # Step 1: Manager decomposes spec into tickets
    tickets = manager.decompose(project_spec, guide.read(), registry.read())
    for ticket in tickets:
        queue.add(ticket)

    # Step 2: Process tickets
    budget = config.max_tickets  # default: 500
    processed = 0

    while processed < budget:
        ticket = queue.next_ready()  # respects depends_on ordering
        if ticket is None:
            break  # all done or all blocked

        # Execute
        git_hash = git.current_hash()
        ticket.git_hash_before = git_hash
        ticket.status = TicketStatus.IN_PROGRESS
        queue.update(ticket)

        result = worker.execute(ticket)

        # Verify
        if result.success:
            verification = verifier.check(ticket.target_file, config.workspace)
            if verification.passed:
                git.commit(f"TICKET {ticket.id}: {ticket.title}")
                ticket.status = TicketStatus.DONE
                ticket.git_hash_after = git.current_hash()
                guide.update_after_ticket(ticket)
                registry.update_after_ticket(ticket)
            else:
                result.success = False
                result.error = verification.errors

        # Handle failure
        if not result.success:
            git.discard_changes()
            ticket.error_log = result.error
            ticket.retry_count += 1

            stuck, reason = is_stuck(ticket, queue.recent_history())
            if stuck:
                ticket = escalation.escalate(ticket, reason)
            else:
                ticket.status = TicketStatus.BACKLOG  # retry later

        queue.update(ticket)
        processed += 1

    return queue.summary()
```

### 4.5 Cloud LLM Stubs

All providers implement `BaseLLM`. Each stub:
- Returns `is_available() = False` when no API key
- Has the full API call structure ready (URL, headers, body format)
- Just needs an API key to activate

```python
# llm/cloud/openai_backend.py
class OpenAIBackend(BaseLLM):
    def __init__(self, config):
        self.api_key = config.get("openai_api_key", "")
        self.model = config.get("openai_model", "gpt-4o-mini")
        self.base_url = "https://api.openai.com/v1/chat/completions"

    def is_available(self) -> bool:
        return bool(self.api_key)

    def generate(self, prompt: str, max_tokens: int = 400) -> LLMResponse:
        if not self.is_available():
            return LLMResponse(text="", model=self.model, tokens_used=0,
                             latency_ms=0, success=False,
                             error="OpenAI API key not configured. Set openai_api_key in config.")
        # Full implementation ready — just needs API key:
        # POST to self.base_url with:
        #   headers: {"Authorization": f"Bearer {self.api_key}"}
        #   body: {"model": self.model, "messages": [{"role": "user", "content": prompt}],
        #          "max_tokens": max_tokens}
        # Handle 429 with exponential backoff
        # Parse response["choices"][0]["message"]["content"]
        raise NotImplementedError("Activate by setting openai_api_key in config")
```

Same pattern for Anthropic, Google, DeepSeek.

### 4.6 LLM Router

```python
class LLMRouter:
    """Try local → cloud → human. Project-agnostic."""

    def __init__(self, config):
        self.local = OllamaBackend(config)
        self.cloud_backends = [
            OpenAIBackend(config),
            AnthropicBackend(config),
            GoogleBackend(config),
            DeepSeekBackend(config),
        ]

    def generate(self, prompt: str, max_tokens: int = 400) -> LLMResponse:
        # 1. Try local
        if self.local.is_available():
            response = self.local.generate(prompt, max_tokens)
            if response.success:
                return response

        # 2. Try cloud (first available)
        for backend in self.cloud_backends:
            if backend.is_available():
                response = backend.generate(prompt, max_tokens)
                if response.success:
                    return response

        # 3. No LLM available — caller must escalate to human
        return LLMResponse(
            text="", model="none", tokens_used=0, latency_ms=0,
            success=False, error="No LLM backend available. Escalate to human."
        )
```

---

## 5. Safety Rules

- Docker isolation for running generated code
- `--network=none` for sandbox containers
- Never `git push --force`
- Always work on branch `nexus/run-{timestamp}`, never main
- Ollama timeout: 30 seconds
- pytest timeout: 60 seconds
- Max tickets per run: 500

---

## 6. Checkpoint System

### 6.1 Agent Checkpoints (SQLite inside workspace)

```sql
CREATE TABLE checkpoints (
    checkpoint_id TEXT PRIMARY KEY,
    ticket_id TEXT,
    git_hash TEXT,
    status TEXT,
    timestamp TEXT,
    error_log TEXT,
    files_changed TEXT
);
```

### 6.2 Builder Checkpoints (you, Gemini Flash)

Maintain `.nexus/checkpoint.md`:

```markdown
# Builder Checkpoint
## Current Phase: [1-7]
## Current Step: [1-18]
## Last Successful Action: [description]

## Experiment Log
| Timestamp | Action | Result | Notes |
|-----------|--------|--------|-------|

## Agent Modifications Log
| Timestamp | File Changed | What Was Wrong | Fix Applied |
|-----------|-------------|----------------|-------------|

## Known Issues
- [ ] ...
```

Update after EVERY significant action.

---

## 7. The Experiment (AFTER Nexus is built)

> [!IMPORTANT]
> Do NOT start this section until the Monitor (Opus 4.6) has reviewed Phase 1 and approved.

### 7.1 Test Case: Twitter Clone

This is just the FIRST test project. We feed Nexus this spec:

```
Create a Python web application called "tweeter" using Flask.
The app needs:
1. User registration (username + password)
2. User login with session management
3. Create a tweet (text only, max 280 chars)
4. View timeline (all tweets, newest first)
Use SQLite for the database. Keep it simple.
```

### 7.2 What to Watch

- Did the Manager produce project-agnostic tickets? (no hardcoded "tweeter" logic in the agent)
- Are tickets properly ordered? (DB schema before routes)
- Is the interface registry updating correctly?
- Is the escalation chain working?

### 7.3 Feature Extension Test

After the base clone works:

```
Add a "like" feature:
1. Users can like/unlike a tweet
2. Each tweet shows its like count
3. A user can only like a tweet once
```

This tests whether Nexus can extend an existing project by reading the current interface registry.

---

## 8. Startup Sequence

```
1. Read all spec files (Section 0)
2. Create .nexus/checkpoint.md
3. Build Phase 1: steps 1-18 from §3.2 (one file at a time, test each)
4. STOP. Update checkpoint.md. Wait for Opus review.
--- (Opus reviews, approves or requests fixes) ---
5. Build Docker files
6. Verify Ollama accessible
7. Build and start container
8. STOP. Update checkpoint.md. Wait for Opus review.
--- (Opus reviews, approves experiment start) ---
9. Run experiment (§7)
10. Monitor and fix
11. Write experiment report
```

---

## 9. Known Issues to Watch For

| # | Issue | Detection | Response |
|---|-------|-----------|----------|
| 1 | Manager produces project-specific code in the agent | Hardcoded app names/routes in manager.py | Rewrite — Manager must be fully generic |
| 2 | Worker outputs markdown instead of Python | Output starts with ``` or has natural language | Fix Worker prompt: "Output ONLY executable Python" |
| 3 | Model thrashing (loading/unloading) | High latency, fan noise | Use ONE model only, pin with keep_alive |
| 4 | SQLite locking | "database is locked" errors | Use WAL mode, single-writer |
| 5 | Ticket context exceeds 500 tokens | Slow/degraded output | Split ticket further |
| 6 | pytest hangs | No return within 60s | Use --timeout=60, kill process group |
| 7 | Interface drift | Integration tests fail | Check interface registry is being updated |
| 8 | Agent writes imports for non-stdlib packages | ImportError | Ticket must list allowed imports |
| 9 | Glue code problem | main.py / app.py gets too big | Use convention-based auto-discovery or split |
| 10 | Manager can't decompose complex specs | Bad/incomplete tickets | This is the hardest problem — may need cloud escalation for planning |
