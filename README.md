# Nexus — Multi-Model Local Coding Agent

Nexus is a local-first, CLI-based multi-model coding agent that orchestrates an ensemble of small models under 3B parameters.

## Installation

Activate the virtual environment and install the package:
```bash
source venv/bin/activate
pip install -e .
```

## Usage

### Check System Status
Show the status of the Ollama backends and the capability score matrix:
```bash
nexus status
```

### Run a Single Goal
Execute a task sequentially (one model call at a time to prevent CPU heating):
```bash
nexus run "Write a python script to merge two sorted lists"
```

### Interactive REPL
Start an interactive chat session:
```bash
nexus chat
```
