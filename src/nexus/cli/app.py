import typer
from nexus.llm.router import ModelRouter
from nexus.loop.engine import Engine

app = typer.Typer(name="nexus", help="Nexus Agent CLI")

@app.command()
def run(
    spec: str = typer.Argument(..., help="Feature/project description to build"),
    workspace: str = typer.Option(None, "--workspace", "-w", help="Workspace path"),
    db: str = typer.Option(None, "--db", "-d", help="SQLite database path")
):
    typer.echo("=== Starting Nexus Agent Execution ===")
    typer.echo(f"Goal: {spec}\n")
    
    router = ModelRouter()
    engine = Engine(router, workspace_dir=workspace, db_path=db)
    
    summary = engine.run(spec)
    typer.echo(summary)

if __name__ == "__main__":
    app()
