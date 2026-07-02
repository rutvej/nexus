# Nexus — Chat Summary and Project Conclusions

This document compiles the engineering discussions, model benchmarking results, and structural conclusions regarding the feasibility of local-first, multi-model AI coding agents.

---

## 1. Executive Summary

The Nexus project aimed to construct a background coding agent utilizing local, sub-3B parameter Large Language Models (LLMs) running on consumer hardware. Over multiple sessions of design, implementation, and benchmarking, the architecture evolved from a simple single-agent runner to a complex, multi-role "Software Consultancy" system. Ultimately, the project was paused due to the physical and cognitive limitations of current sub-3B models, though new specialized model architectures like `gemma4:e2b` offer potential avenues for future exploration.

---

## 2. Core Architectural Evolutions

### 2.1 The "Software Consultancy" Paradigm
To combat the reasoning limits of sub-3B models, the architecture split the agent's cognition into three distinct roles:
1.  **Manager (Strategy & Deconstruction):** Decomposes high-level prompts into granular Scrum tickets, tracking progress on a board and managing shadow git branches.
2.  **Senior Developer (Test-First/TDD):** Writes unit tests defining success criteria *before* code is implemented.
3.  **Junior Developer (Implementation):** Writes the minimal code required to pass the test, iterating on raw test runner tracebacks.

### 2.2 Production Safety Gates
To prevent small models from failing silently or damaging the host system:
*   **Salted Context Gates:** Wrapped untrusted file reads in unique cryptographic tags to isolate model prompts.
*   **Static Analysis Gates:** Intercepted code outputs and ran deterministic checks (`black`, `mypy`, `bandit`) rather than relying on LLM-based code reviews.
*   **Isolated Subprocesses:** Executed terminal commands in dedicated Unix process groups (`os.setsid`) to guarantee clean timeouts and prevent zombie processes.

---

## 3. Key Failure Modes & Bottlenecks

Through real-world evaluation, several critical bottlenecks were identified:

1.  **The TDD Debugging Death Spiral:** When a sub-3B model generates a broken test, the implementing model gets trapped in an infinite loop trying to satisfy impossible assertions.
2.  **Context Saturation & Attention Drift:** Small attention mechanisms degrade rapidly once the prompt context exceeds 1,500 tokens, leading the model to ignore system rules or hallucinate.
3.  **VRAM/Model Thrashing:** Switching between different models (e.g., Gemma for planning, Qwen for coding) forces Ollama to load and unload models continuously. On local CPUs, this generates high latency and extreme thermal heat, spinning up hardware fans.
4.  **Negative ROI:** Babysitting a small model to write a simple function often takes longer than writing the code manually, leading to negative developer productivity.

---

## 4. The Edge Specialist Paradigm (`gemma4:e2b`)

In the final phase of the discussion, we analyzed the newly released **`gemma4:e2b`** model (Google DeepMind, April 2026), which presents solutions to these limitations:
*   **128K Context Window:** Resolves attention degradation over long codebase histories.
*   **2B Active Parameters (MoE):** Limits active inference computation to preserve local CPU power and eliminate cooling fan noise.
*   **Native Function Calling:** Eliminates fragile JSON parsing layers by natively structuring tool invocation.

While promising, the model still faces "needle-in-a-haystack" attention dilution and high CPU pre-fill latency, making local autonomous loops highly experimental.

---

## 5. Current Project Status

*   **Status:** **PAUSED**
*   **Compute Cleanup:** All local model weights (`gemma2:2b`, `qwen3.5:2b`, `qwen2.5-coder:1.5b`, and `qwen2.5:1.5b`) were successfully removed from the local Ollama instances to free up disk space.
*   **Docker Services:** The underlying Docker containers (including the Ollama container running on port `11435`) remain **ONLINE** and unaffected.
