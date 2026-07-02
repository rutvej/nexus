import os
import pytest
from nexus.tickets.models import Ticket, TicketType, TicketStatus
from nexus.tickets.queue import TicketQueue

@pytest.fixture
def temp_db(tmp_path):
    db_file = tmp_path / "test_tickets.db"
    return str(db_file)

def test_add_and_get_ticket(temp_db):
    queue = TicketQueue(db_path=temp_db)
    ticket = Ticket(
        id="T1",
        type=TicketType.CREATE_FILE,
        title="Test Ticket",
        depends_on=["DEP1"]
    )
    queue.add_ticket(ticket)
    
    retrieved = queue.get_ticket("T1")
    assert retrieved is not None
    assert retrieved.id == "T1"
    assert retrieved.title == "Test Ticket"
    assert retrieved.type == TicketType.CREATE_FILE
    assert retrieved.depends_on == ["DEP1"]

def test_update_ticket(temp_db):
    queue = TicketQueue(db_path=temp_db)
    ticket = Ticket(
        id="T1",
        type=TicketType.CREATE_FILE,
        title="Test Ticket"
    )
    queue.add_ticket(ticket)
    
    ticket.status = TicketStatus.IN_PROGRESS
    ticket.retry_count = 1
    queue.update_ticket(ticket)
    
    retrieved = queue.get_ticket("T1")
    assert retrieved.status == TicketStatus.IN_PROGRESS
    assert retrieved.retry_count == 1

def test_get_next_runnable_ticket(temp_db):
    queue = TicketQueue(db_path=temp_db)
    
    # T1 has dependency T2
    t1 = Ticket(
        id="T1",
        type=TicketType.WRITE_FUNCTION,
        title="T1",
        depends_on=["T2"]
    )
    # T2 has no dependencies
    t2 = Ticket(
        id="T2",
        type=TicketType.WRITE_TEST,
        title="T2"
    )
    
    queue.add_ticket(t1)
    queue.add_ticket(t2)
    
    # T2 should be runnable, T1 should not (since T2 is not done)
    runnable = queue.get_next_runnable_ticket()
    assert runnable is not None
    assert runnable.id == "T2"
    
    # Complete T2
    t2.status = TicketStatus.DONE
    queue.update_ticket(t2)
    
    # T1 should now be runnable
    runnable = queue.get_next_runnable_ticket()
    assert runnable is not None
    assert runnable.id == "T1"
