# Nexus — 2026 Agent Capabilities & Roadmap

This document analyzes modern (2026) agent paradigms, evaluates their feasibility for sub-3B parameter local models running on CPU-only hardware, and outlines the roadmap for future development.

---

## 1. Modern Agent Paradigms (2026)

### 1.1 Model Context Protocol (MCP)
*   **What it is:** An open standard developed by Anthropic for connecting AI models to secure data sources and tools (e.g., databases, GitHub, Slack).
*   **Feasibility for Sub-3B Models:** **Low-Medium (Add to Think List).**
    *   *Challenge:* Negotiating the MCP protocol, parsing complex schemas, and handling multi-turn tool handshakes requires substantial reasoning capacity and consumes precious context window tokens.
    *   *Decision:* Keep it as a future plugin extension. For now, use direct, lightweight Python tool wrappers.

### 1.2 Test-Driven Development (TDD) Loop
*   **What it is:** The agent automatically writes a unit test representing the user's requirement, runs it to watch it fail, implements the code, and runs the test again until it passes.
*   **Feasibility for Sub-3B Models:** **High (Implementable).**
    *   *Why:* Sub-3B models (like `qwen2.5:1.5b`) are excellent at writing simple unit tests and fixing code based on raw traceback errors.
    *   *Roadmap:* Integrate this directly into the `AgentCore` execution loop as an automated verification step.

### 1.3 Unified Diff / Patch Editing
*   **What it is:** Instead of rewriting a whole file (which is slow and expensive), the model outputs a unified diff, which is applied via a patch tool.
*   **Feasibility for Sub-3B Models:** **High (Implementable).**
    *   *Why:* Drastically reduces token generation count (improving speed on CPU) and keeps the model focused on the changed lines.
    *   *Roadmap:* Replace `write_file` and `replace_text` with a dedicated `apply_patch` tool.

### 1.4 Context Window Compression
*   **What it is:** Dynamically compressing, summarizing, or pruning conversation history and repository context to fit within small context windows (2K–8K).
*   **Feasibility for Sub-3B Models:** **High (Required).**
    *   *Why:* Sub-3B models degrade rapidly in quality when their context window is full.
    *   *Roadmap:* Implement token-budget-aware context pruning (e.g., using `qwen3.5:2b` to summarize previous conversation turns).

---

## 2. Technical Roadmap & TODOs

### Phase 1: Core Enhancements (Feasible for Sub-3B)
- [ ] **TDD Mode:** Enable the agent to write a `test_*.py` file and run `pytest` via `terminal_exec` to verify its own work.
- [ ] **Unified Diff Tool:** Implement a `patch` tool that applies standard unified diffs.
- [ ] **Context Windowing:** Add a sliding window tokenizer to truncate conversation history when approaching the model's context limit.
- [ ] **Multi-turn Planning:** Allow the planner to dynamically add new steps based on the outputs of previous steps.

### Phase 2: Advanced Integrations (Future / Think List)
- [ ] **MCP Client:** Implement a lightweight MCP client to connect to local databases or filesystem servers.
- [ ] **Structural RAG:** Use tree-sitter to parse code into a symbol dependency graph for smarter code retrieval.
- [ ] **Spec-first Development:** Require the agent to write a specification markdown file before implementing any new feature.
