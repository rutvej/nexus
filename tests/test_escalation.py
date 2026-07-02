from nexus.tickets.models import Ticket, TicketType, TicketStatus
from nexus.tickets.escalation import is_stuck

def test_is_stuck_max_retries():
    t = Ticket(
        id="T-1",
        type=TicketType.WRITE_FUNCTION,
        title="T1",
        status=TicketStatus.FAILED,
        target_file="t.py",
        retry_count=3
    )
    stuck, reason = is_stuck(t, [])
    assert stuck is True
    assert reason == "max_retries_exceeded"

def test_is_stuck_consecutive_failures():
    t = Ticket(
        id="T-6",
        type=TicketType.WRITE_FUNCTION,
        title="T6",
        status=TicketStatus.FAILED,
        target_file="t.py",
        retry_count=0
    )
    history = [
        Ticket(id="T-1", type=TicketType.WRITE_FUNCTION, title="T1", status=TicketStatus.FAILED, target_file="t.py"),
        Ticket(id="T-2", type=TicketType.WRITE_FUNCTION, title="T2", status=TicketStatus.FAILED, target_file="t.py"),
        Ticket(id="T-3", type=TicketType.WRITE_FUNCTION, title="T3", status=TicketStatus.FAILED, target_file="t.py"),
        Ticket(id="T-4", type=TicketType.WRITE_FUNCTION, title="T4", status=TicketStatus.FAILED, target_file="t.py"),
        Ticket(id="T-5", type=TicketType.WRITE_FUNCTION, title="T5", status=TicketStatus.FAILED, target_file="t.py")
    ]
    stuck, reason = is_stuck(t, history)
    assert stuck is True
    assert reason == "consecutive_failure_streak"

def test_is_stuck_identical_output():
    t = Ticket(
        id="T-1",
        type=TicketType.WRITE_FUNCTION,
        title="T1",
        status=TicketStatus.FAILED,
        target_file="t.py",
        retry_count=1,
        llm_output="def add(): return 1"
    )
    history = [
        Ticket(id="T-1", type=TicketType.WRITE_FUNCTION, title="T1", status=TicketStatus.FAILED, target_file="t.py", llm_output="def add(): return 1")
    ]
    stuck, reason = is_stuck(t, history)
    assert stuck is True
    assert reason == "identical_output_loop"
