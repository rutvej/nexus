from dataclasses import dataclass, field
from enum import Enum
from typing import List

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
    id: str
    type: TicketType
    title: str
    status: TicketStatus
    
    # MANDATORY CONTEXT
    target_file: str
    function_signature: str = ""
    parameters: str = ""
    return_type: str = ""
    dependencies: str = ""
    related_interfaces: str = ""
    description: str = ""
    
    # EXECUTION STATE
    retry_count: int = 0
    max_retries: int = 3
    error_log: str = ""
    llm_output: str = ""
    git_hash_before: str = ""
    git_hash_after: str = ""
    
    # DEPENDENCIES
    depends_on: List[str] = field(default_factory=list)
    blocks: List[str] = field(default_factory=list)
    epic: str = "Epic"
    
    # ESCALATION
    escalation_note: str = ""
    human_feedback: str = ""
