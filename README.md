# Nexus: Multi-Model Local Coding Agent Sandbox

Nexus is an agentic, local-first code synthesis platform. It orchestrates local LLMs running via **Ollama** to decompose goals into a structured ticket backlog, implement code iteratively, run multi-stage test-driven verification, and execute self-correcting git-commit loops.

This project is fully automated and designed to run inside a sandboxed Docker container, making it safe to execute generated code.

---

## 🚀 Agent Quick Start

### 1. Prerequisites Setup

Before running the agent, make sure the following dependencies are installed and running:
* **Docker** (with daemon running)
* **Python 3.10+** (recommended 3.12)
* **Ollama** (running on host port `11435`)

#### Installing Local Dependencies (For host tools)
```bash
# Set up a python virtual environment
python3 -m venv venv
source venv/bin/activate

# Install the nexus CLI package in editable mode
pip install -e .
```

#### Pulling the Required Models
Make sure you have pulled the required LLM model via Ollama. For the lightweight CPU-conscious run, use `gemma4:e2b` (5.1B parameters, optimized for coding tasks):
```bash
# Pull model directly through Ollama
ollama pull gemma4:e2b

# Alternatively, pull via the helper script:
# (Uses Ollama host at port 11435)
./nexus.sh pull-model
```

---

## 🏃 Running the Experiment

To run the experiment, use the unified `nexus.sh` helper script. It manages Docker compilation, workspace mounting, data volume mapping, and log capture.

### Run with CPU and Thread Limits (Recommended for Gemma 4)
Because local inference is highly CPU-intensive, you should limit both the container CPU quota and Ollama's generation threads to prevent overheating and timeouts.

Run the experiment with **2 CPUs and 2 Ollama generation threads**:
```bash
# Cleans workspace/DB, rebuilds the Docker image, and starts the run
NEXUS_CPUS=2 NEXUS_NUM_THREAD=2 ./nexus.sh run --rebuild --model gemma4:e2b
```

### Resume a Failed Run
If a ticket escalates or the process terminates prematurely, you can resume execution without wiping your progress:
```bash
# Resumes the execution loop using gemma4:e2b, retrying escalated tickets
NEXUS_CPUS=2 NEXUS_NUM_THREAD=2 ./nexus.sh resume --model gemma4:e2b
```

### Fast Host Mode (No Docker)
To test LLM outputs directly on your host environment without the overhead of container building/running:
```bash
./run_fast.sh --model gemma4:e2b
```

---

## 📊 Monitoring Progress

You can monitor the agent's work in real-time using these three methods:

### 1. CLI Status Check
Check which tickets are in the backlog, in progress, done, or escalated, along with error tracebacks:
```bash
./nexus.sh status
```

### 2. Live Agent Logs
Tail the logs from the active Docker container:
```bash
./nexus.sh logs
```

### 3. Web Dashboard
Nexus includes a visual web dashboard to inspect tickets, generated files, and execution timelines:
```bash
./nexus.sh dashboard
```
Open **[http://localhost:8050](http://localhost:8050)** in your browser to view it.

---

## 🧹 Cleaning and Resetting the Workspace

To start a completely fresh experiment, you must reset the git state of the nested `workspace` directory and delete all database session cache files. Run the following commands:

```bash
# 1. Reset the nested workspace repository to the clean baseline branch
cd workspace
git checkout nexus/main
git reset --hard HEAD
git clean -fd
cd ..

# 2. Delete the generated source/test folders and the SQLite session database
rm -rf workspace/src workspace/tests
rm -f data/session.db data/session.db-shm data/session.db-wal
```

---

## ⚙️ How the Agent Works Under the Hood

When you execute a goal, the Nexus framework operates in a loop:
1. **Decomposition**: The model splits the main goal into small atomic implementation tickets (stored in `data/session.db`).
2. **Worker Selection**: For each ticket in order, a workspace is configured, and the LLM writes/edits code.
3. **Verification Pipeline**:
   - **Syntax verification**: Python syntax checking.
   - **Import verification**: Checks if modules are correctly importable.
   - **Undefined names verification**: Runs `mypy` to statically check for missing variables/imports.
   - **Test verification**: Runs `pytest` to execute unit tests against the generated code.
4. **Git Loop**: If checks pass, the agent commits the code. If checks fail, the agent retries (up to 3 times) using the error stack trace before escalating the ticket.
