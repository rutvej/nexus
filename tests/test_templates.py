from nexus.tickets.models import Ticket, TicketType, TicketStatus
from nexus.tickets.templates import validate_ticket, WRITE_FUNCTION_PROMPT

def test_validate_ticket_success():
    t = Ticket(
        id="T-1",
        type=TicketType.WRITE_FUNCTION,
        title="T1",
        status=TicketStatus.BACKLOG,
        target_file="src/math.py",
        function_signature="def add(a, b)",
        description="Add two numbers"
    )
    valid, err = validate_ticket(t)
    assert valid is True
    assert err == ""

def test_validate_ticket_too_large():
    t = Ticket(
        id="T-1",
        type=TicketType.WRITE_FUNCTION,
        title="T1",
        status=TicketStatus.BACKLOG,
        target_file="src/math.py",
        description="A" * 2100
    )
    valid, err = validate_ticket(t)
    assert valid is False
    assert "too large" in err

def test_validate_ticket_no_file():
    t = Ticket(
        id="T-1",
        type=TicketType.WRITE_FUNCTION,
        title="T1",
        status=TicketStatus.BACKLOG,
        target_file=""
    )
    valid, err = validate_ticket(t)
    assert valid is False
    assert "target_file" in err

def test_template_rendering():
    prompt = WRITE_FUNCTION_PROMPT.format(
        function_signature="def add(a, b)",
        parameters="a, b",
        return_type="int",
        dependencies="None",
        description="Add a and b",
        related_interfaces="None"
    )
    assert "def add(a, b)" in prompt
    assert "Add a and b" in prompt
