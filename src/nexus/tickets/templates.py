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
- Write ONLY the function body. No imports, no tests, no comments outside the function."""

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

CRITICAL RULES:
- Use ONLY the Python standard library (e.g. sqlite3) and Flask. Do NOT import or use SQLAlchemy, Django, or any other third-party ORMs/libraries.
- Write ONLY the corrected function body. No imports, no tests."""

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
