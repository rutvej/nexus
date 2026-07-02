from nexus.tickets.models import Ticket, TicketType, TicketStatus
from nexus.tickets.queue import TicketQueue

def test_queue_in_memory():
    q = TicketQueue(":memory:")
    t1 = Ticket(
        id="T-01",
        type=TicketType.CREATE_FILE,
        title="T1",
        status=TicketStatus.BACKLOG,
        target_file="t1.py"
    )
    t2 = Ticket(
        id="T-02",
        type=TicketType.WRITE_FUNCTION,
        title="T2",
        status=TicketStatus.BACKLOG,
        target_file="t2.py",
        depends_on=["T-01"]
    )
    
    q.add_ticket(t1)
    q.add_ticket(t2)
    
    # Next ready should be T-01, since T-02 is blocked by T-01
    ready = q.next_ready()
    assert ready is not None
    assert ready.id == "T-01"
    
    # Mark T-01 as DONE
    t1.status = TicketStatus.DONE
    q.update_ticket(t1)
    
    # Next ready should now be T-02
    ready = q.next_ready()
    assert ready is not None
    assert ready.id == "T-02"
