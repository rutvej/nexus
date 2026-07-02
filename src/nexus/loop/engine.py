import os
from nexus.tickets.models import Ticket, TicketStatus, TicketType
from nexus.tickets.queue import TicketQueue
from nexus.tickets.escalation import is_stuck
from nexus.agent.manager import Manager
from nexus.agent.worker import Worker
from nexus.agent.verifier import Verifier
from nexus.project.guide import ProjectGuide
from nexus.project.interface_registry import InterfaceRegistry
from nexus.project.git_ops import GitOperations
from nexus import config

class Engine:
    def __init__(self, router, workspace_dir: str = None, db_path: str = None):
        self.workspace_dir = workspace_dir or str(config.WORKSPACE_DIR)
        self.db_path = db_path or str(config.DB_PATH)
        
        self.queue = TicketQueue(self.db_path)
        self.guide = ProjectGuide(self.workspace_dir)
        self.registry = InterfaceRegistry(self.guide)
        self.git = GitOperations(self.workspace_dir)
        
        self.manager = Manager(router, self.queue, self.guide)
        self.worker = Worker(router, self.workspace_dir)
        self.verifier = Verifier(self.workspace_dir)

    def run(self, project_spec: str, max_steps: int = 500) -> str:
        """
        Runs the main loop to build the requested project spec.
        Returns a summary string of the execution results.
        """
        # Step 1: Decompose feature request into tickets
        try:
            self.manager.decompose_feature(project_spec)
        except Exception as e:
            return f"Decomposition failed: {e}"

        steps = 0
        while steps < max_steps:
            ticket = self.queue.next_ready()
            if not ticket:
                # No runnable tickets left
                break

            ticket.status = TicketStatus.IN_PROGRESS
            ticket.git_hash_before = self.git.get_current_head_hash()
            self.queue.update_ticket(ticket)

            # Let worker generate code
            worker_success = self.worker.execute_ticket(ticket)

            if worker_success:
                # Run verifications: AST parsing & test suite
                syntax_ok, syntax_err = self.verifier.verify_syntax(ticket.target_file)
                if syntax_ok:
                    # Pre-format code
                    self.verifier.auto_format(ticket.target_file)
                    
                    # Run tests (runs all tests or the specific test file)
                    # If it's a WRITE_TEST ticket, run the test file. Otherwise run all tests in tests/
                    test_file_to_run = ticket.target_file if ticket.type == TicketType.WRITE_TEST else "tests"
                    tests_ok, test_output = self.verifier.run_tests(test_file_to_run)
                    
                    if tests_ok:
                        # PASS: Commit changes, update registry and save, mark DONE
                        self.git.commit_ticket_changes(ticket.id, ticket.title)
                        ticket.status = TicketStatus.DONE
                        ticket.git_hash_after = self.git.get_current_head_hash()
                        
                        # If a function was added, add it to Interface Registry
                        if ticket.type == TicketType.WRITE_FUNCTION and ticket.function_signature:
                            self.registry.add_signature(
                                ticket.target_file,
                                ticket.function_signature,
                                ticket.description
                            )
                            self.registry.save()
                    else:
                        worker_success = False
                        ticket.error_log = f"Tests failed:\n{test_output}"
                else:
                    worker_success = False
                    ticket.error_log = f"Syntax verification failed:\n{syntax_err}"

            if not worker_success:
                # FAIL: Rollback file changes
                self.git.rollback_changes()
                ticket.retry_count += 1
                
                # Check if stuck
                history = self.queue.recent_history()
                stuck, reason = is_stuck(ticket, history)
                if stuck:
                    ticket.status = TicketStatus.ESCALATED
                    ticket.escalation_note = f"Stuck due to {reason}. Output trace: {ticket.error_log}"
                else:
                    # Send back to backlog for retry
                    ticket.status = TicketStatus.BACKLOG

            self.queue.update_ticket(ticket)
            steps += 1

        # Return a status summary
        all_t = self.queue.list_all()
        done = len([t for t in all_t if t.status == TicketStatus.DONE])
        escalated = len([t for t in all_t if t.status == TicketStatus.ESCALATED])
        return f"Completed {done}/{len(all_t)} tickets. Escalated: {escalated}."
