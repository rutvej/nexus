import typer
import os
import sys
import datetime
from rich.console import Console
from rich.table import Table

from nexus import config
from nexus.tickets.models import Ticket, TicketType, TicketStatus
from nexus.tickets.queue import TicketQueue
from nexus.tickets.templates import validate_ticket
from nexus.tickets.escalation import EscalationHandler
from nexus.llm.ollama_backend import OllamaLLM
from nexus.llm.cloud_stub import OpenAILLM, GoogleLLM, AnthropicLLM, DeepSeekLLM
from nexus.llm.router import ModelRouter
from nexus.project.guide import ProjectGuide
from nexus.project.interface_registry import InterfaceRegistry
from nexus.project.git_ops import GitOperations
from nexus.agent.verifier import Verifier
from nexus.agent.worker import Worker
from nexus.agent.manager import Manager

app = typer.Typer(help="Nexus — Ticket-Based Local Coding Agent")
console = Console()

def get_router() -> ModelRouter:
    local_llm = OllamaLLM()
    cloud_llms = [
        OpenAILLM(),
        GoogleLLM(),
        AnthropicLLM(),
        DeepSeekLLM()
    ]
    return ModelRouter(local_llm=local_llm, cloud_llms=cloud_llms)

@app.command()
def status():
    """Show the status of Ollama models and the ticket queue."""
    try:
        router = get_router()
        console.print("\n[bold green]=== Nexus System Status ===[/bold green]")
        
        # 1. Ollama status
        ollama_status = "[green]ONLINE[/green]" if router.local_llm.is_available() else "[red]OFFLINE[/red]"
        console.print(f"Ollama Host ({config.OLLAMA_HOST}): {ollama_status}")
        console.print(f"Active Local Model: [cyan]{config.MODEL_NAME}[/cyan]\n")

        # 2. Queue status
        queue = TicketQueue()
        tickets = queue.list_tickets()
        
        if not tickets:
            console.print("Ticket queue is empty.")
            return

        table = Table(title="Nexus Ticket Queue Summary", show_header=True, header_style="bold magenta")
        table.add_column("Status", style="bold")
        table.add_column("Count", justify="center")
        
        status_counts = {status: 0 for status in TicketStatus}
        for t in tickets:
            status_counts[t.status] += 1
            
        for status, count in status_counts.items():
            color = "white"
            if status == TicketStatus.DONE:
                color = "green"
            elif status in (TicketStatus.FAILED, TicketStatus.ESCALATED):
                color = "red"
            elif status == TicketStatus.IN_PROGRESS:
                color = "yellow"
            table.add_row(f"[{color}]{status.value.upper()}[/{color}]", str(count))
            
        console.print(table)
        console.print()
    except Exception as e:
        console.print(f"[bold red]Error checking status:[/bold red] {e}")
        sys.exit(1)

@app.command()
def run(goal: str = typer.Argument(..., help="The feature request or task goal for the agent to build")):
    """Run the agent on a high-level task goal."""
    console.print(f"\n[bold green]=== Starting Nexus Agent Execution ===[/bold green]")
    console.print(f"Goal: [cyan]{goal}[/cyan]\n")
    
    try:
        # Initialize dependencies
        router = get_router()
        queue = TicketQueue()
        guide = ProjectGuide()
        registry = InterfaceRegistry(guide)
        git_ops = GitOperations()
        verifier = Verifier()
        worker = Worker(router)
        manager = Manager(router, queue, guide)
        escalation_handler = EscalationHandler(queue)
        
        # Step 1: Decompose feature
        console.print("[bold yellow]Decomposing feature request into tickets...[/bold yellow]")
        tickets = manager.decompose_feature(goal)
        console.print(f"Successfully enqueued [green]{len(tickets)}[/green] tickets.\n")
        
        # Step 2: Execution Loop
        run_count = 0
        max_runs = config.MAX_RETRIES_PER_TICKET * len(tickets) + 10  # safety cap
        
        while run_count < max_runs:
            ticket = queue.get_next_runnable_ticket()
            
            if not ticket:
                # No more runnable tickets. Check if we are done or stuck.
                all_tickets = queue.list_tickets()
                done_count = sum(1 for t in all_tickets if t.status == TicketStatus.DONE)
                escalated_count = sum(1 for t in all_tickets if t.status == TicketStatus.ESCALATED)
                
                if done_count == len(all_tickets):
                    console.print("\n[bold green]🎉 Success! All tickets completed successfully.[/bold green]\n")
                    sys.exit(0)
                elif escalated_count > 0:
                    console.print(f"\n[bold red]❌ Execution halted: {escalated_count} tickets escalated.[/bold red]\n")
                    sys.exit(1)
                else:
                    # No runnable ticket, none escalated, but not all done.
                    # This could be a deadlock or dependency circularity.
                    console.print("\n[bold red]❌ Execution halted: Queue deadlock or unresolved dependencies.[/bold red]\n")
                    sys.exit(1)
            
            # Start executing the ticket
            run_count += 1
            console.print(f"[bold blue]Processing {ticket.id} ({ticket.type.value}): {ticket.title}[/bold blue]")
            console.print(f"  Target File: {ticket.target_file}")
            
            ticket.status = TicketStatus.IN_PROGRESS
            ticket.started_at = datetime.datetime.now().isoformat()
            queue.update_ticket(ticket)
            
            # Create checkpoint tag
            git_ops.create_checkpoint_tag()
            
            try:
                # 1. Execute ticket using LLM
                worker.execute_ticket(ticket)
                
                # 2. Verifications
                # A. Syntax check
                syntax_ok, syntax_err = verifier.verify_syntax(ticket.target_file)
                if not syntax_ok:
                    console.print(f"  [red]Syntax check failed:[/red] {syntax_err}")
                    raise ValueError(syntax_err)
                
                # B. Formatting check & fix
                verifier.auto_format(ticket.target_file)
                
                # C. Run tests
                # If it's a test file, run it directly. Otherwise, run all tests in tests/
                test_file_to_run = ticket.target_file if ticket.type == TicketType.WRITE_TEST else "tests"
                
                # Verify tests if any tests exist in the folder
                tests_passed, test_output = verifier.run_tests(test_file_to_run)
                if not tests_passed:
                    console.print(f"  [red]Test verification failed.[/red]")
                    raise ValueError(test_output)
                
                # 3. Commit and finish on success
                ticket.status = TicketStatus.DONE
                ticket.completed_at = datetime.datetime.now().isoformat()
                queue.update_ticket(ticket)
                
                # Register interface in registry if WRITE_FUNCTION
                if ticket.type == TicketType.WRITE_FUNCTION:
                    registry.register_interface(
                        file_path=ticket.target_file,
                        function_signature=ticket.function_signature,
                        description=ticket.description
                    )
                
                git_ops.commit_ticket_changes(ticket.id, ticket.title)
                console.print(f"  [green]Passed all verifications and committed.[/green]\n")
                
            except Exception as e:
                # Execution failed -> trigger escalation / rollback
                error_msg = str(e)
                console.print(f"  [red]Failure during execution:[/red] {error_msg}")
                
                escalated, reason = escalation_handler.handle_failure(ticket, error_msg)
                
                # Rollback repository changes
                git_ops.rollback_changes()
                
                if escalated:
                    console.print(f"  [red]Ticket {ticket.id} ESCALATED: {reason}[/red]\n")
                else:
                    console.print(f"  [yellow]Ticket {ticket.id} FAILED. Will retry (Attempt {ticket.retry_count}/{ticket.max_retries}).[/yellow]\n")

        console.print("[bold red]❌ Execution halted: Maximum run budget exceeded.[/bold red]")
        sys.exit(1)
        
    except Exception as e:
        console.print(f"[bold red]Critical Error during run:[/bold red] {e}")
        sys.exit(1)

if __name__ == "__main__":
    app()
