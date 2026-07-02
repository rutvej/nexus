from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, List
import datetime

class TicketStatus(Enum):
    BACKLOG = "backlog"
    IN_PROGRESS = "in_progress"
    TESTING = "testing"
    DONE = "done"
    FAILED = "failed"
    ESCALATED = "escalated"

class TicketType(Enum):
    CREATE_FILE = "create_file"
    WRITE_FUNCTION = "write_function"
    WRITE_TEST = "write_test"
    RUN_TESTS = "run_tests"
    FIX_BUG = "fix_bug"
    INTEGRATION_TEST = "integration_test"

@dataclass
class Ticket:
    id: str                                    # e.g., "TWIT-001"
    type: TicketType
    title: str                                 # e.g., "Write function create_user"
    status: TicketStatus = TicketStatus.BACKLOG
    
    # === MANDATORY CONTEXT ===
    target_file: str = ""                      # e.g., "src/models/user.py"
    function_signature: str = ""               # e.g., "def create_user(username: str, password: str) -> dict"
    parameters: str = ""                       # e.g., "username: str, password: str"
    return_type: str = ""                      # e.g., "dict with keys: id, username, password_hash"
    dependencies: str = ""                     # e.g., "import sqlite3, import hashlib"
    related_interfaces: str = ""               # Signatures of functions this depends on
    description: str = ""                      # What the function should do (1-2 sentences)
    
    # === EXECUTION STATE ===
    retry_count: int = 0
    max_retries: int = 3
    error_log: str = ""
    llm_output: str = ""
    git_hash_before: str = ""
    git_hash_after: str = ""
    
    # === DEPENDENCIES ===
    depends_on: List[str] = field(default_factory=list)
    blocks: List[str] = field(default_factory=list)
    epic: str = ""
    
    # === TIMESTAMPS ===
    created_at: str = field(default_factory=lambda: datetime.datetime.now().isoformat())
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    
    # === ESCALATION ===
    escalation_note: str = ""
    human_feedback: str = ""
