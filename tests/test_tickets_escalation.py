import pytest
from nexus.tickets.models import Ticket, TicketType, TicketStatus
from nexus.tickets.queue import TicketQueue
from nexus.tickets.escalation import EscalationHandler

@pytest.fixture
def temp_db(tmp_path):
    return str(tmp_path / "test_escalation.db")

def test_escalation_max_retries(temp_db):
    queue = TicketQueue(db_path=temp_db)
    handler = EscalationHandler(queue)
    
    ticket = Ticket(id="T1", type=TicketType.WRITE_FUNCTION, title="test", retry_count=3, max_retries=3)
    queue.add_ticket(ticket)
    
    escalated, reason = handler.handle_failure(ticket, "Assertion failed")
    assert escalated is True
    assert reason == "max_retries_exceeded"
    
    db_ticket = queue.get_ticket("T1")
    assert db_ticket.status == TicketStatus.ESCALATED
    assert "Max retries" in db_ticket.escalation_note

def test_escalation_identical_output(temp_db):
    queue = TicketQueue(db_path=temp_db)
    handler = EscalationHandler(queue)
    
    ticket = Ticket(id="T1", type=TicketType.WRITE_FUNCTION, title="test", retry_count=1, max_retries=3, llm_output="def add(a, b): pass")
    queue.add_ticket(ticket)
    
    # Run handle_failure with the same llm_output
    escalated, reason = handler.handle_failure(ticket, "Syntax error")
    assert escalated is True
    assert reason == "identical_output_loop"
    
    db_ticket = queue.get_ticket("T1")
    assert db_ticket.status == TicketStatus.ESCALATED
    assert "Identical output" in db_ticket.escalation_note

def test_no_escalation_normal_retry(temp_db):
    queue = TicketQueue(db_path=temp_db)
    handler = EscalationHandler(queue)
    
    ticket = Ticket(id="T1", type=TicketType.WRITE_FUNCTION, title="test", retry_count=0, max_retries=3, llm_output="first output")
    queue.add_ticket(ticket)
    
    # Change output for retry to avoid identical output check
    ticket.llm_output = "second output"
    
    escalated, reason = handler.handle_failure(ticket, "First failure")
    assert escalated is False
    assert reason is None
    
    db_ticket = queue.get_ticket("T1")
    assert db_ticket.status == TicketStatus.FAILED
    assert db_ticket.retry_count == 1
