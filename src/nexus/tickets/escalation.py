from nexus import config
from nexus.tickets.models import Ticket, TicketStatus
from nexus.tickets.queue import TicketQueue

class EscalationHandler:
    def __init__(self, queue: TicketQueue):
        self.queue = queue

    def handle_failure(self, ticket: Ticket, error_msg: str) -> tuple[bool, str | None]:
        """
        Processes a ticket failure. Checks for loop detection rules.
        If stuck, marks status as ESCALATED and returns (True, reason).
        If not stuck, increments retry_count, marks status as FAILED, and returns (False, None).
        """
        ticket.error_log = error_msg

        # Rule 1: Max retries per ticket
        # If we have already hit or exceeded the limit, escalate
        if ticket.retry_count >= ticket.max_retries:
            ticket.status = TicketStatus.ESCALATED
            ticket.escalation_note = f"Max retries ({ticket.max_retries}) exceeded. Last error: {error_msg}"
            self.queue.update_ticket(ticket)
            return True, "max_retries_exceeded"

        # Rule 2: Identical outputs loop
        # Compare with the previous version stored in DB
        db_ticket = self.queue.get_ticket(ticket.id)
        if db_ticket and db_ticket.llm_output and db_ticket.llm_output == ticket.llm_output:
            ticket.status = TicketStatus.ESCALATED
            ticket.escalation_note = f"Identical output detected twice. Loop prevention triggered. Last error: {error_msg}"
            self.queue.update_ticket(ticket)
            return True, "identical_output_loop"

        # Rule 3: Consecutive failures across all tickets in queue
        all_tickets = self.queue.list_tickets()
        # Filter tickets that are not in backlog or in_progress, and sort by completed_at
        non_active = [t for t in all_tickets if t.status in (TicketStatus.FAILED, TicketStatus.ESCALATED, TicketStatus.DONE)]
        non_active.sort(key=lambda x: x.completed_at or x.created_at)
        
        recent = non_active[-config.MAX_CONSECUTIVE_FAILURES:]
        if len(recent) >= config.MAX_CONSECUTIVE_FAILURES and all(t.status in (TicketStatus.FAILED, TicketStatus.ESCALATED) for t in recent):
            ticket.status = TicketStatus.ESCALATED
            ticket.escalation_note = f"Consecutive failure streak ({config.MAX_CONSECUTIVE_FAILURES}) hit across the project queue."
            self.queue.update_ticket(ticket)
            return True, "consecutive_failure_streak"

        # No loop detected: update retry count and set to FAILED for retry
        ticket.retry_count += 1
        ticket.status = TicketStatus.FAILED
        self.queue.update_ticket(ticket)
        return False, None
