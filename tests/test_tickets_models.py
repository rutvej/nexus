from nexus.tickets.models import Ticket, TicketType, TicketStatus

def test_ticket_creation():
    t = Ticket(
        id="TWIT-001",
        type=TicketType.WRITE_FUNCTION,
        title="Write function create_user",
        target_file="src/models/user.py",
        function_signature="def create_user(username: str) -> dict"
    )
    assert t.id == "TWIT-001"
    assert t.type == TicketType.WRITE_FUNCTION
    assert t.status == TicketStatus.BACKLOG
    assert t.target_file == "src/models/user.py"
    assert t.function_signature == "def create_user(username: str) -> dict"
    assert t.retry_count == 0
    assert t.max_retries == 3
    assert isinstance(t.depends_on, list)
    assert t.created_at is not None
