from nexus.tickets.models import Ticket, TicketStatus

MAX_RETRIES_PER_TICKET = 3
MAX_CONSECUTIVE_FAILURES = 5

def is_stuck(ticket: Ticket, history: list[Ticket]) -> tuple[bool, str]:
    # Rule 1: Ticket retries exceeded
    if ticket.retry_count >= MAX_RETRIES_PER_TICKET:
        return True, "max_retries_exceeded"
        
    # Rule 2: Too many consecutive failures across all tickets
    recent = history[-MAX_CONSECUTIVE_FAILURES:]
    if len(recent) == MAX_CONSECUTIVE_FAILURES and all(t.status == TicketStatus.FAILED for t in recent):
        return True, "consecutive_failure_streak"
        
    # Rule 3: Model producing identical output
    if ticket.retry_count >= 1:
        # Find all versions of this ticket in history that have llm_output
        same_id_tickets = [t for t in history if t.id == ticket.id and t.llm_output]
        outputs = [t.llm_output for t in same_id_tickets]
        if ticket.llm_output:
            outputs.append(ticket.llm_output)
        # If there are duplicates in outputs, it's an identical output loop
        if len(outputs) >= 2 and len(set(outputs)) < len(outputs):
            return True, "identical_output_loop"
            
    return False, ""
