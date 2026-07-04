import typer
from nexus.llm.router import ModelRouter
from nexus.loop.engine import Engine

app = typer.Typer(name="nexus", help="Nexus Agent CLI")

@app.command()
def run(
    spec: str = typer.Argument(..., help="Feature/project description to build"),
    workspace: str = typer.Option(None, "--workspace", "-w", help="Workspace path"),
    db: str = typer.Option(None, "--db", "-d", help="SQLite database path"),
    resume: bool = typer.Option(False, "--resume", "-r", help="Resume: retry escalated tickets without re-decomposing")
):
    typer.echo("=== Starting Nexus Agent Execution ===")
    typer.echo(f"Goal: {spec}\n")
    if resume:
        typer.echo("  Mode: RESUME (retrying escalated tickets)\n")
    
    router = ModelRouter()
    engine = Engine(router, workspace_dir=workspace, db_path=db)
    
    summary = engine.run(spec, resume=resume)
    typer.echo(summary)

if __name__ == "__main__":
    app()

