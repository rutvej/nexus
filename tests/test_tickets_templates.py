from nexus.tickets.models import Ticket, TicketType
from nexus.tickets.templates import validate_ticket, render_ticket_prompt

def test_validate_valid_ticket():
    ticket = Ticket(
        id="TWIT-001",
        type=TicketType.WRITE_FUNCTION,
        title="Write create_user",
        target_file="src/models/user.py",
        function_signature="def create_user(username: str) -> dict",
        description="Creates a new user dict"
    )
    valid, msg = validate_ticket(ticket)
    assert valid is True
    assert msg == ""

def test_validate_missing_fields():
    ticket = Ticket(
        id="TWIT-001",
        type=TicketType.WRITE_FUNCTION,
        title="Write create_user"
    )
    valid, msg = validate_ticket(ticket)
    assert valid is False
    assert "target_file" in msg

def test_validate_token_limit():
    ticket = Ticket(
        id="TWIT-001",
        type=TicketType.WRITE_FUNCTION,
        title="Write create_user",
        target_file="src/models/user.py",
        function_signature="def create_user(username: str) -> dict",
        description="A" * 2500  # Very long description to exceed 500 tokens
    )
    valid, msg = validate_ticket(ticket)
    assert valid is False
    assert "exceeds the limit" in msg

def test_render_prompt():
    ticket = Ticket(
        id="TWIT-001",
        type=TicketType.WRITE_FUNCTION,
        title="Write create_user",
        target_file="src/models/user.py",
        function_signature="def create_user(username: str) -> dict",
        description="Creates a new user dict"
    )
    prompt = render_ticket_prompt(ticket)
    assert "def create_user" in prompt
    assert "Creates a new user dict" in prompt
