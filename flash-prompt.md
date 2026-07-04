# Phase 3.1 — Continuation Prompt

## What's Done
- Nexus agent source code is **100% general-purpose** (zero hardcoded app references)
- Verification pipeline: `syntax → importable → mypy undefined names → black format → pytest`
- Auto-generated WRITE_TEST tickets (no reliance on 1.5B model for test planning)
- Prompt templates enforce: stdlib+Flask only, `CREATE TABLE IF NOT EXISTS`, include typing/datetime imports
- All 36 unit tests pass, pushed to `nexus/experiment-001`

## What Failed (2 Experiment Runs)
Both runs: **3/8 tickets completed, 4 escalated.** Same failure modes:

| Failure | Count | Root Cause |
|---------|-------|------------|
| Functions return `None` instead of objects | 2 | Model doesn't reliably write `return` statements |
| `NameError: List not defined` | 1 | Model uses `List[Tweet]` without importing `typing` |
| Duplicate class declarations in same file | 2 | Worker appends code blindly, re-declaring imports + classes |
| `TypeError: missing positional argument` | 1 | Second class declaration has different `__init__` signature |

## The 3 Fixes To Apply (In Order)

### Fix 1: Smart File Merge in Worker (CRITICAL — Bug Fix)

The Worker's `WRITE_FUNCTION` append mode blindly concatenates code. When `create_user` and `login_user` both target `src/models/user.py`, the second append re-declares `import sqlite3` and `class User` with a different `__init__` signature, breaking the first function.

**In `src/nexus/agent/worker.py`**, before appending to an existing file:
1. Parse the existing file with `ast.parse()` to find all existing import statements, class names, and function names
2. Parse the new code the same way
3. Skip any imports that already exist in the file
4. Skip any class declarations that already exist in the file
5. Only append new function definitions and truly new imports

```python
def _deduplicate_code(self, existing_content: str, new_code: str) -> str:
    """Remove from new_code any imports or class defs that already exist in existing_content."""
    import ast
    
    try:
        existing_tree = ast.parse(existing_content)
    except SyntaxError:
        return new_code  # Can't parse, just append as-is
    
    # Collect existing names
    existing_imports = set()
    existing_classes = set()
    existing_functions = set()
    for node in ast.walk(existing_tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                existing_imports.add(f"import {alias.name}")
        elif isinstance(node, ast.ImportFrom):
            existing_imports.add(f"from {node.module}")
        elif isinstance(node, ast.ClassDef):
            existing_classes.add(node.name)
        elif isinstance(node, ast.FunctionDef):
            existing_functions.add(node.name)
    
    # Filter new code line-by-line
    lines = new_code.splitlines()
    filtered = []
    skip_block = False
    skip_indent = 0
    
    for line in lines:
        stripped = line.strip()
        
        # Check if this starts a class we already have
        class_match = re.match(r'^class\s+(\w+)', stripped)
        if class_match and class_match.group(1) in existing_classes:
            skip_block = True
            skip_indent = len(line) - len(line.lstrip())
            continue
            
        # If we're skipping a class block, skip until dedent
        if skip_block:
            if stripped == '' or (len(line) - len(line.lstrip()) > skip_indent):
                continue
            else:
                skip_block = False
        
        # Skip duplicate imports
        if stripped.startswith('import ') and stripped in existing_imports:
            continue
        if stripped.startswith('from ') and any(stripped.startswith(ei) for ei in existing_imports):
            continue
            
        filtered.append(line)
    
    return '\n'.join(filtered)
```

Then call `_deduplicate_code()` in `execute_ticket()` before writing to the file when it already exists.

### Fix 2: Inject Existing File Content into Prompts

When writing a function to a file that already exists, the model NEEDS to see what's already in the file — especially class definitions it must match.

**In `src/nexus/agent/worker.py`**, when building the `WRITE_FUNCTION` prompt:
```python
if os.path.exists(full_path):
    with open(full_path, "r") as f:
        existing = f.read()
    prompt += f"\n\nEXISTING FILE CONTENT (your function must work with this code):\n```python\n{existing}\n```"
```

### Fix 3: Auto-Fix Common Import Patterns

**In `src/nexus/agent/worker.py`**, add a post-processing step after `extract_code()`:

```python
def _auto_fix_imports(self, code: str) -> str:
    """Add missing imports for common patterns the model forgets."""
    lines = code.splitlines()
    needed_imports = []
    
    code_str = code
    if 'List[' in code_str or 'Optional[' in code_str or 'Dict[' in code_str or 'Tuple[' in code_str:
        needed_imports.append('from typing import List, Optional, Dict, Tuple')
    if 'datetime.' in code_str or 'datetime(' in code_str:
        needed_imports.append('from datetime import datetime')
    
    # Only add imports that aren't already present
    existing_code = '\n'.join(lines)
    new_imports = [imp for imp in needed_imports if imp not in existing_code]
    
    if new_imports:
        return '\n'.join(new_imports) + '\n\n' + code
    return code
```

## After Applying Fixes
```bash
# 1. Run unit tests
./venv/bin/pytest

# 2. Clean workspace
rm -rf /home/rutvej/nexus/workspace/src /home/rutvej/nexus/workspace/tests
rm -f /home/rutvej/nexus/data/session.db data/session.db-shm data/session.db-wal

# 3. Rebuild Docker
docker build -t nexus-agent -f docker/Dockerfile.nexus .

# 4. Re-run experiment
docker run --rm -u 1000:1000 \
  -v /home/rutvej/nexus/workspace:/workspace \
  -v /home/rutvej/nexus/data:/data \
  --add-host host.docker.internal:host-gateway \
  -e OLLAMA_HOST=http://host.docker.internal:11435 \
  -e NEXUS_DATA_DIR=/data \
  -e NEXUS_WORKSPACE_DIR=/workspace \
  nexus-agent:latest \
  "Create a Python web application called 'tweeter' using Flask. The app needs: 1. User registration (username + password) 2. User login with session management 3. Create a tweet (text only, max 280 chars) 4. View timeline (all tweets, newest first). Use SQLite for the database. Keep it simple."

# 5. Check results
python3 -c "import sqlite3; conn = sqlite3.connect('data/session.db'); cursor = conn.cursor(); cursor.execute('SELECT id, type, status, retry_count FROM tickets'); [print(row) for row in cursor.fetchall()]"
```

## Success Criteria
- **Minimum:** 6/8 tickets pass (all 4 source files + at least 2 test files)
- **Target:** 8/8 tickets pass
- **If <6/8 with fixes above:** Try `qwen2.5-coder:7b` model (pull with `ollama pull qwen2.5-coder:7b`)

## After Phase 3 Passes
1. **Feature Extension Test:** Ask the agent to add a "like" feature to validate extensibility
2. **Push final code to git**
3. **Update checkpoint.md**
