# Builder Checkpoint

## Current Phase: 3.1 — Experiment Iteration
## Current Step: Fix Worker file merge, then re-run experiment
## Last Successful Action: Added mypy verify_undefined_names, updated prompt templates, all 36 tests pass, pushed to nexus/experiment-001
## Nexus Agent Status: stopped
## Date: 2026-07-02

---

## Session 2 Changes (2026-07-02, ~19:47–19:58 UTC)

### Code Changes Applied
1. **templates.py** — Added 2 new CRITICAL RULES to both `WRITE_FUNCTION_PROMPT` and `FIX_BUG_PROMPT`:
   - `CREATE TABLE IF NOT EXISTS` before any SQLite queries
   - Include all `typing`/`datetime` imports if using them
2. **verifier.py** — Added `verify_undefined_names()` method using `sys.executable -m mypy --check-untyped-defs --ignore-missing-imports` to catch `[name-defined]` errors statically
3. **engine.py** — Integrated `verify_undefined_names()` into verification pipeline: syntax → importable → undefined names → format → tests
4. **test_engine.py** — Renamed `math.py` → `addition.py` in mock to avoid stdlib collision; added import to mock test output
5. **test_verifier.py** — Added unit test for `verify_undefined_names` (valid file passes, file with `datetime.now()` without import fails)

### Experiment Runs
| Run | Template Changes | Mypy Check | Result | Notes |
|-----|-----------------|------------|--------|-------|
| Run 1 | ✅ SQLite/typing rules | ❌ Not yet | 3/8 done, 4 escalated | Same failures as session 1 |
| Run 2 | ✅ | ✅ | Not completed — permission timeout | Docker image was rebuilt with all fixes |

### Git State
- Branch: `nexus/experiment-001`
- HEAD: `739939e` — "Fix unit tests and implement verify_undefined_names check"
- All 36 tests pass
- Pushed to `origin/nexus/experiment-001`

---

## Session 1 Changes (2026-07-02, ~05:00–16:30 UTC)

### Code Changes Applied
1. **worker.py** — CREATE_FILE→WRITE_FUNCTION fallback for tickets with `function_signature`; sanitized `dependencies` parsing (comma/semicolon/newline splitting, strips ticket ID hallucinations, auto-prefixes `import`)
2. **engine.py** — Auto-generates `WRITE_TEST` tickets for every `WRITE_FUNCTION`/`CREATE_FILE` ticket with a signature; dynamically populates `related_interfaces` from registry before execution
3. **verifier.py** — Added `verify_importable()` runtime import check
4. **interface_registry.py** — Includes Python module import path (e.g. `src.models.tweet`) in `get_related_interfaces()` output
5. **templates.py** — Added CRITICAL RULES to restrict libraries to stdlib + Flask
6. **git_ops.py** — Auto `git init` on fresh workspace, safe branch checkouts
7. **worker.py** — `_replace_function_in_code()` for in-place FIX_BUG edits
8. **cloud/*.py** — Raise `NotImplementedError` when API key set

---

## Diagnosed Problems (Unresolved)

### P1: Worker File-Append Duplicates Declarations (BUG)
When multiple WRITE_FUNCTION tickets target the same file, Worker appends blindly → duplicate `import sqlite3`, duplicate `class User`, conflicting `__init__` signatures. This causes downstream tickets to fail.

**Fix:** Parse existing file with `ast` before appending. Skip existing imports/classes. Only append new function defs.

### P2: 1.5B Model Can't Self-Correct (CAPABILITY LIMIT)
`qwen2.5-coder:1.5b` ignores error tracebacks in FIX_BUG retries. It regenerates similar bad code and hits the 3-retry escalation limit without improvement.

**Fix:** Try `qwen2.5-coder:7b` as a drop-in. Or add auto-fix heuristics for common patterns (missing imports, missing return statements).

### P3: Dependent Tickets Lack Source Context (QUALITY)
When writing `login_user`, the model doesn't see the actual `class User` code — only a one-line interface summary. The 1.5B model needs exact code, not abstractions.

**Fix:** Read the target file's existing content and inject it into the prompt as `EXISTING FILE CONTENT:`.

---

## Next Steps (In Order)

### Step 1: Fix Worker File Merge Logic
In `worker.py`, before appending to an existing file:
- Use `ast.parse()` to find existing imports, class defs, and function defs
- Skip any import lines the model re-declares
- Skip any class definitions that already exist
- Only write the new function definition

### Step 2: Inject Existing File Content into Prompts
In `worker.py`, for WRITE_FUNCTION tickets where the file already exists:
- Read the current file content
- Include it in the prompt: `EXISTING FILE CONTENT:\n{content}\n\nWrite your function to work with the code above.`
- This gives the model the actual class signatures to match

### Step 3: Add Auto-Fix Import Heuristics
In `worker.py` or as a post-processing step:
- If code contains `List[`, `Dict[`, `Optional[` → auto-add `from typing import List, Dict, Optional`
- If code contains `datetime.` → auto-add `from datetime import datetime`
- Deduplicate all import lines

### Step 4: Re-run Experiment
```bash
rm -rf /home/rutvej/nexus/workspace/src /home/rutvej/nexus/workspace/tests
rm -f /home/rutvej/nexus/data/session.db /home/rutvej/nexus/data/session.db-shm /home/rutvej/nexus/data/session.db-wal
docker build -t nexus-agent -f docker/Dockerfile.nexus .
docker run --rm -u 1000:1000 \
  -v /home/rutvej/nexus/workspace:/workspace \
  -v /home/rutvej/nexus/data:/data \
  --add-host host.docker.internal:host-gateway \
  -e OLLAMA_HOST=http://host.docker.internal:11435 \
  -e NEXUS_DATA_DIR=/data \
  -e NEXUS_WORKSPACE_DIR=/workspace \
  nexus-agent:latest \
  "Create a Python web application called 'tweeter' using Flask. The app needs: 1. User registration (username + password) 2. User login with session management 3. Create a tweet (text only, max 280 chars) 4. View timeline (all tweets, newest first). Use SQLite for the database. Keep it simple."
```

### Step 5: If >6/8 Tickets Pass → Feature Extension Test
Ask the agent to add a "like" feature to validate extensibility.

### Step 6: If Still <6/8 → Try Larger Model
Switch to `qwen2.5-coder:7b`:
```bash
ollama pull qwen2.5-coder:7b
# Update OLLAMA_HOST or model config to use qwen2.5-coder:7b
```

---

## Environment Reference
- **Ollama**: running on host port `11435`, model `qwen2.5-coder:1.5b`
- **Docker image**: `nexus-agent:latest` (rebuilt with mypy + typing fixes)
- **Container user**: always `-u 1000:1000` to avoid permission issues
- **DB cleanup**: must delete `session.db`, `session.db-shm`, AND `session.db-wal` together
- **Workspace cleanup**: delete `workspace/src` and `workspace/tests` (keep `.git`, `.nexus`)
