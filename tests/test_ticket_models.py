from nexus.tickets.models import Ticket, TicketType, TicketStatus

def test_ticket_creation():
    t = Ticket(
        id="TKT-001",
        type=TicketType.CREATE_FILE,
        title="Test Ticket",
        status=TicketStatus.BACKLOG,
        target_file="test.py"
    )
    assert t.id == "TKT-001"
    assert t.type == TicketType.CREATE_FILE
    assert t.status == TicketStatus.BACKLOG
    assert t.target_file == "test.py"
    assert t.retry_count == 0
    assert t.depends_on == []
