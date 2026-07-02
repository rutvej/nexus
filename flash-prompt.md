# Phase 3 Prompt for Gemini Flash 3.5

## Paste this into your Flash conversation NOW

---

**Excellent work on Phase 2!** The Docker container `nexus-agent:latest` is built and verified, and all 33 unit tests pass.

Now we begin **Phase 3: The Live Experiment (Twitter Clone)**.

We will now put our project-agnostic Nexus agent to the test by asking it to build a Twitter clone from scratch inside its Docker container using the local sub-3B model (`qwen2.5-coder:1.5b` running on host port `11435`).

### 1. Launch the Nexus Agent in Docker

Run the following command in your terminal to start the agent:

```bash
docker run --rm \
  -v /home/rutvej/nexus/workspace:/workspace \
  -v /home/rutvej/nexus/data:/data \
  --add-host host.docker.internal:host-gateway \
  -e OLLAMA_HOST=http://host.docker.internal:11435 \
  -e NEXUS_DATA_DIR=/data \
  -e NEXUS_WORKSPACE_DIR=/workspace \
  nexus-agent:latest \
  "Create a Python web application called 'tweeter' using Flask. The app needs: 1. User registration (username + password) 2. User login with session management 3. Create a tweet (text only, max 280 chars) 4. View timeline (all tweets, newest first). Use SQLite for the database. Keep it simple."
```

### 2. Monitor Agent Execution

While or after the container runs:
1. Inspect the generated tickets inside the SQLite database `/home/rutvej/nexus/data/session.db` (or check console logs).
2. Watch files being generated inside `/home/rutvej/nexus/workspace/`.
3. **If Nexus succeeds:** Verify that the code in `/home/rutvej/nexus/workspace/` has unit tests and passes syntax/test verification.
4. **If Nexus gets stuck or errors out:** Diagnose the root cause. If it's a bug in how Nexus parses LLM output or manages files, fix the relevant file in `src/nexus/`, rebuild the docker image (`docker build -t nexus-agent -f docker/Dockerfile.nexus .`), and re-run.

### 3. Checkpoint & Return

Once the agent completes the run (or processes at least 15-20 tickets):
1. Record the experiment results in `/home/rutvej/nexus/.nexus/checkpoint.md` under the **Experiment Log** section. Note what worked and any failures.
2. Tell me to switch back here for review and to prepare the final validation test (adding the "like" feature).
