from nexus.tickets.models import Ticket, TicketType

WRITE_FUNCTION_TEMPLATE = """Write a Python function with this exact signature:

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
do not write comments outside the function. Avoid repeating the function signature.
"""

def estimate_tokens(text: str) -> int:
    """Rough conservative token count estimate (chars // 4 or words * 1.3)."""
    if not text:
        return 0
    char_estimate = len(text) // 4
    word_estimate = int(len(text.split()) * 1.3)
    return max(char_estimate, word_estimate)

def render_ticket_prompt(ticket: Ticket) -> str:
    """Renders the prompt for a WRITE_FUNCTION ticket."""
    if ticket.type == TicketType.WRITE_FUNCTION:
        return WRITE_FUNCTION_TEMPLATE.format(
            function_signature=ticket.function_signature,
            parameters=ticket.parameters,
            return_type=ticket.return_type,
            dependencies=ticket.dependencies,
            description=ticket.description,
            related_interfaces=ticket.related_interfaces
        )
    else:
        # Generic template for other ticket types
        return f"Task type: {ticket.type.value}\nTitle: {ticket.title}\nDescription: {ticket.description}\nTarget file: {ticket.target_file}\n"

def validate_ticket(ticket: Ticket) -> tuple[bool, str]:
    """
    Validates a ticket.
    Key Invariant: context fields must total <= 500 tokens when rendered.
    """
    # 1. Check mandatory fields based on type
    if not ticket.id:
        return False, "Ticket ID is missing"
    
    if ticket.type == TicketType.WRITE_FUNCTION:
        if not ticket.target_file:
            return False, "target_file is required for WRITE_FUNCTION"
        if not ticket.function_signature:
            return False, "function_signature is required for WRITE_FUNCTION"
        if not ticket.description:
            return False, "description is required for WRITE_FUNCTION"
    elif ticket.type in (TicketType.CREATE_FILE, TicketType.WRITE_TEST, TicketType.FIX_BUG, TicketType.INTEGRATION_TEST):
        if not ticket.target_file:
            return False, f"target_file is required for {ticket.type.value}"
        if not ticket.description:
            return False, f"description is required for {ticket.type.value}"
    elif ticket.type == TicketType.RUN_TESTS:
        if not ticket.target_file:
            return False, "target_file is required for RUN_TESTS"

    # 2. Token limit validation
    context_text = (
        ticket.target_file +
        ticket.function_signature +
        ticket.parameters +
        ticket.return_type +
        ticket.dependencies +
        ticket.related_interfaces +
        ticket.description
    )
    token_count = estimate_tokens(context_text)
    if token_count > 500:
        return False, f"Context fields total {token_count} tokens, which exceeds the limit of 500 tokens"

    return True, ""
