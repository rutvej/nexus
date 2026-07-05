from nexus.tickets.models import Ticket

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

CRITICAL RULES:
- Use ONLY the Python standard library (e.g. sqlite3) and Flask. Do NOT import or use SQLAlchemy, Django, or any other third-party ORMs/libraries.
- If you use SQLite, ALWAYS run `CREATE TABLE IF NOT EXISTS ...` before executing database insert/select queries to ensure the tables exist.
- Ensure all necessary imports (including typing, database, or other models from the project guide like `from src.models.user import User`) are written at the top of your code block if you use them.
- Output ONLY the function definition, imports, and function body. No tests, no example usages, and no markdown/comments outside of the code block."""

WRITE_TEST_PROMPT = """Write a pytest test function for:

{function_signature}

The function:
{description}

Expected return type:
{return_type}

CRITICAL RULES:
- You MUST import the function under test from {target_file} (e.g. `from {target_file} import ...`).
- Inspect the source code of the module under test (provided below if available) to ensure class names, attribute names, and return types match exactly. Do not guess class properties.
- Do NOT redefine, copy, or mock the function you are testing. You must test the actual implementation.
- Do NOT use @pytest.fixture or any pytest fixtures. Put ALL setup and teardown code DIRECTLY INSIDE the test function body.
- If testing database functions: they use SQLite and write to a .db file (e.g. `users.db` or `tweets.db`). At the START of your test function, delete the .db file if it exists using `import os; os.remove('users.db') if os.path.exists('users.db') else None` to ensure a clean state.
- If testing database query/getter functions (like view_timeline or login_user): you MUST first insert mock test data (e.g., insert users or tweets) into the database at the start of your test. Connect using `sqlite3.connect('dbname.db')`, create the necessary tables if they do not exist, run insert queries, commit, and close. NEVER write plain SQL text directly to the database file via `open('dbname.db', 'w')`.
- Write exactly ONE test function named `test_<function_name>`. Include at least 3 assertions.
- Output ONLY the test function and its imports. No fixtures, no classes, no markdown."""

FIX_BUG_PROMPT = """Fix this Python function. The test failed with this error:

Function:
{function_signature}

Error traceback:
{error_log}

The function should:
{description}

CRITICAL RULES:
- Use ONLY the Python standard library (e.g. sqlite3) and Flask. Do NOT import or use SQLAlchemy, Django, or any other third-party ORMs/libraries.
- If you use SQLite, ALWAYS run `CREATE TABLE IF NOT EXISTS ...` before executing database insert/select queries to ensure the tables exist.
- Ensure all necessary imports (including typing, database, or other models from the project guide like `from src.models.user import User`) are written at the top of your code block if you use them.
- Output ONLY the corrected function definition, imports, and function body. No tests, no example usages, and no markdown/comments outside of the code block."""

def validate_ticket(ticket: Ticket) -> tuple[bool, str]:
    """
    Validates ticket fields. Ensures target_file is not empty.
    Checks that the compiled context is <= 500 tokens.
    Uses a conservative estimation: 1 token = 4 characters, or word count * 1.3.
    """
    if not ticket.target_file:
        return False, "target_file is mandatory"
    
    # Check context size limit of 500 tokens
    context_text = (
        ticket.target_file +
        ticket.function_signature +
        ticket.parameters +
        ticket.return_type +
        ticket.dependencies +
        ticket.related_interfaces +
        ticket.description
    )
    
    # 500 tokens is roughly 2000 characters. Let's enforce <= 2000 chars.
    if len(context_text) > 2000:
        return False, f"Ticket context is too large ({len(context_text)} chars > 2000 chars limit)"
        
    return True, ""
