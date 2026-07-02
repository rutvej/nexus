import typer
import os
import sys
from rich.console import Console
from rich.table import Table

from nexus.config.config import Config
from nexus.models.router import ModelRouter
from nexus.tools.registry import ToolRegistry
from nexus.tools.executor import ToolExecutor
from nexus.agent.core import AgentCore
from nexus.benchmark.engine import BenchmarkEngine

# Import built-in tools
from nexus.tools.builtins.file_ops import FileReadTool, FileWriteTool, ListDirTool, ReplaceTextTool
from nexus.tools.builtins.terminal import TerminalExecTool

app = typer.Typer(help="Nexus — Multi-Model Local Coding Agent")
console = Console()

def get_agent() -> AgentCore:
    config = Config()
    router = ModelRouter()
    
    # Initialize and register tools
    registry = ToolRegistry()
    registry.register(FileReadTool())
    registry.register(FileWriteTool())
    registry.register(ListDirTool())
    registry.register(ReplaceTextTool())
    registry.register(TerminalExecTool())
    
    executor = ToolExecutor(registry, config)
    return AgentCore(config, router, registry, executor)

@app.command()
def run(goal: str = typer.Argument(..., help="The goal or instruction for the agent to achieve")):
    """Run the agent on a single goal."""
    try:
        agent = get_agent()
        result = agent.run(goal)
        if result["success"]:
            sys.exit(0)
        else:
            sys.exit(1)
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        sys.exit(1)

@app.command()
def status():
    """Show the status of the Ollama models and the Nexus score matrix."""
    try:
        router = ModelRouter()
        
        console.print("\n[bold green]=== Nexus System Status ===[/bold green]")
        console.print("[bold]Active Backends & Models:[/bold]")
        
        for host, backend in router.backends.items():
            status_str = "[green]ONLINE[/green]" if backend.is_available() else "[red]OFFLINE[/red]"
            console.print(f"  - {host}: {status_str}")
            
        # Print score matrix
        scores = router.scores
        if not scores:
            console.print("\nNo model scores recorded.")
            return
            
        models = sorted(list(scores.keys()))
        task_types = sorted(list(next(iter(scores.values()))["scores"].keys()))
        
        table = Table(title="\nNEXUS MODEL CAPABILITY SCORE MATRIX", show_header=True, header_style="bold magenta")
        table.add_column("Model", style="cyan", width=20)
        for t in task_types:
            table.add_column(t, justify="center")
            
        for m in models:
            row = [m]
            for t in task_types:
                val = scores[m]["scores"].get(t, 0.0)
                row.append(f"{val:.2f}")
            table.add_row(*row)
            
        console.print(table)
        console.print()
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")

@app.command()
def benchmark():
    """Run the benchmark suite on all available models and update the score matrix."""
    try:
        router = ModelRouter()
        engine = BenchmarkEngine(router)
        console.print("\n[bold green]=== Starting Nexus Model Benchmarking ===[/bold green]")
        console.print("Running benchmarks to evaluate and update model scores...")
        
        run_id = engine.run_all()
        
        console.print(f"\n[bold green]🎉 Benchmarking complete! (Run ID: {run_id})[/bold green]")
        # Show updated status/matrix
        status()
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")

@app.command()
def chat():
    """Start an interactive chat session with the Nexus agent (REPL)."""
    console.print("\n[bold green]=== Welcome to the Nexus Interactive REPL ===[/bold green]")
    console.print("Type your goal to start the agent, or type [bold]/exit[/bold] to quit.\n")
    
    agent = get_agent()
    
    while True:
        try:
            goal = input("nexus> ").strip()
            if not goal:
                continue
            if goal.lower() in ("/exit", "exit", "quit"):
                console.print("[yellow]Goodbye![/yellow]")
                break
                
            agent.run(goal)
            console.print("\n" + "-" * 60 + "\n")
        except KeyboardInterrupt:
            console.print("\n[yellow]Session interrupted. Type /exit to quit.[/yellow]\n")
        except Exception as e:
            console.print(f"[bold red]Error:[/bold red] {e}\n")

if __name__ == "__main__":
    app()
