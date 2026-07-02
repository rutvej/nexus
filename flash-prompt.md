# Phase 3 Review — Opus Analysis

## Verdict: The AGENT is general-purpose ✅ — but Flash is confused about what to do next

Let me be very clear about what's happening:

### What's Actually Going On

1. **The Nexus agent source code (`src/nexus/`) IS general-purpose.** Zero Twitter references. I grep'd it. Clean.
2. **The Docker experiment DID run.** Nexus received the Twitter clone spec, the sub-3B model (`qwen2.5-coder:1.5b`) decomposed it into 4 tickets, and 3/4 completed successfully.
3. **Flash (conversation 330d) is NOT rebuilding a Twitter agent** — it's monitoring the Nexus experiment output and trying to fix the one ESCALATED ticket (TKT-004: `get_timeline`).

So the agent itself is fine. The problem is the **experiment results reveal real bugs in how Nexus handles sub-3B model output**.

---

## Experiment Results Analysis

### What Nexus Produced (workspace/)

| File | Content | Quality |
|------|---------|---------|
| `src/models/user.py` | `create_user()` + `login_user()` | ⚠️ Bad — uses SQLAlchemy (not in deps), `login_user` calls non-existent `authenticate_user()` and `get_user_by_username()` |
| `src/models/tweet.py` | `Tweet` class + `create_tweet()` | ⚠️ OK-ish — no persistence, just creates in-memory object |
| `src/views/timeline.py` | `get_timeline()` | ❌ ESCALATED — model hallucinated ticket ID `TKT-003` as raw text into the code |

### Root Causes

| # | Bug | Where | Impact |
|---|-----|-------|--------|
| **1** | **Model hallucinates ticket IDs into code** | The `dependencies` field on TKT-004 was literally `"TKT-003"` (a ticket reference, not a Python import). The worker wrote `TKT-003` as a line of code. | `SyntaxError: leading zeros in decimal integer literals` |
| **2** | **No test tickets generated** | The Manager prompt says "Always write a test ticket" but the sub-3B model only generated 4 WRITE_FUNCTION tickets with zero WRITE_TEST tickets. | No verification possible |
| **3** | **Model imports non-existent modules** | `user.py` line 27: `from .models import User` — the model hallucinated a relative import that doesn't exist | ImportError at runtime |
| **4** | **Model uses libraries not in the spec** | `user.py` uses `sqlalchemy` — the spec said "Use SQLite" but the model chose SQLAlchemy ORM which isn't installed | ImportError |
| **5** | **Interface registry not used in decomposition** | `related_interfaces` is always `""` on every ticket, so the model doesn't know what functions already exist when writing dependent code | Functions call non-existent helpers |

---

## 5 Fixes Before Re-Running

### Fix 1: Sanitize `dependencies` field in Worker (CRITICAL)
The model sometimes puts ticket IDs (like `"TKT-003"`) in the dependencies field instead of Python imports. The worker already strips `TKT-` lines from code output, but it doesn't sanitize the `dependencies` field before writing it as an import line.

**In `worker.py` line 98-102:** The existing sanitization is good but needs to also handle comma-separated ticket IDs like `"TKT-001, TKT-002"`.

### Fix 2: Force Manager to generate test tickets
The decomposition prompt asks for test tickets but the 1.5B model ignores this. Two options:
- **Option A (simpler):** After Manager generates tickets, the Engine automatically creates a `WRITE_TEST` ticket for every `WRITE_FUNCTION` ticket (deterministic, no LLM needed).
- **Option B:** Make the prompt more forceful.

**Recommendation:** Option A — don't rely on a 1.5B model to plan properly.

### Fix 3: Populate `related_interfaces` from registry
In `manager.py` line 95, `related_interfaces` is hardcoded to `""`. The Manager should read the current Interface Registry and populate this field so dependent functions know what's available.

### Fix 4: Restrict imports to stdlib + specified packages
Add a validation step in the Verifier that checks imports against an allowed list (stdlib + packages listed in the project spec). Reject code that imports `sqlalchemy`, `django`, etc. unless explicitly requested.

### Fix 5: Engine should validate generated code can actually run
Before marking a ticket DONE, verify that `ast.parse` catches not just syntax errors but also obvious import errors by checking if imported modules exist.

---

## Corrective Prompt for Flash (Phase 3.1)

Paste this into your Flash conversation:

---

**STOP. Opus has reviewed the Phase 3 results.**

The agent source code is confirmed general-purpose ✅. The problem is the sub-3B model produces messy output that Nexus doesn't handle robustly enough. Here are 3 fixes to apply, then re-run the experiment.

### Fix 1: Auto-generate test tickets in Engine (MOST IMPORTANT)

In `src/nexus/loop/engine.py`, after the Manager decomposes the spec into tickets (line 35), add a post-processing step that automatically creates a `WRITE_TEST` ticket for every `WRITE_FUNCTION` ticket. Do NOT rely on the 1.5B model to generate test tickets — it won't.

```python
# After manager.decompose_feature(), add:
all_tickets = self.queue.list_all()
test_tickets = []
for t in all_tickets:
    if t.type == TicketType.WRITE_FUNCTION and t.function_signature:
        test_ticket = Ticket(
            id=f"{t.id}-TEST",
            type=TicketType.WRITE_TEST,
            title=f"Test for {t.title}",
            status=TicketStatus.BACKLOG,
            target_file=f"tests/test_{os.path.basename(t.target_file)}",
            function_signature=t.function_signature,
            parameters=t.parameters,
            return_type=t.return_type,
            dependencies=t.dependencies,
            related_interfaces=t.related_interfaces,
            description=f"Write pytest tests for {t.function_signature}",
            depends_on=[t.id],
            epic=t.epic
        )
        test_tickets.append(test_ticket)
for tt in test_tickets:
    self.queue.add_ticket(tt)
```

### Fix 2: Populate `related_interfaces` in Manager

In `src/nexus/agent/manager.py`, after creating each ticket, populate `related_interfaces` from the Interface Registry:

```python
# In decompose_feature(), after creating ticket t:
t.related_interfaces = self.guide.get_section("Interface Registry")[:500]  # trim to fit context
```

Also add the Interface Registry content to the DECOMPOSE_PROMPT_TEMPLATE:
```
INTERFACE REGISTRY (existing functions):
{interface_registry}
```

### Fix 3: Validate dependencies field in Worker

In `src/nexus/agent/worker.py`, in the dependencies sanitization block, also strip entries that look like ticket IDs or non-import text. A simple check:

```python
# Only write dependencies that look like valid Python imports
if deps and not re.match(r"^TKT-", deps, re.IGNORECASE):
    # Also ensure each line looks like "import X" or "from X import Y"
    valid_deps = []
    for dep_line in deps.split(","):
        dep_line = dep_line.strip()
        if dep_line.startswith("import ") or dep_line.startswith("from "):
            valid_deps.append(dep_line)
        elif dep_line and not re.match(r"^TKT-", dep_line, re.IGNORECASE):
            valid_deps.append(f"import {dep_line}")
    if valid_deps:
        f.write("\n".join(valid_deps) + "\n\n")
```

### After applying fixes:
1. Clear the workspace: `rm -rf /home/rutvej/nexus/workspace/src /home/rutvej/nexus/workspace/tests`
2. Clear the session DB: `rm -f /home/rutvej/nexus/data/session.db`
3. Rebuild Docker: `docker build -t nexus-agent -f docker/Dockerfile.nexus .`
4. Re-run the experiment with the same Twitter clone spec
5. Update `.nexus/checkpoint.md` and tell me to switch back to Opus

---
