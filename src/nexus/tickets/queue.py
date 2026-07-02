import sqlite3
import json
import os
from typing import Optional, List
from nexus import config
from nexus.tickets.models import Ticket, TicketStatus, TicketType

class TicketQueue:
    def __init__(self, db_path: str = None):
        self.db_path = db_path or str(config.DB_PATH)
        # Ensure parent directory exists
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self._init_db()

    def _get_connection(self):
        conn = sqlite3.connect(self.db_path)
        # Use WAL mode for concurrency, as specified in specs
        conn.execute("PRAGMA journal_mode=WAL;")
        return conn

    def _init_db(self):
        with self._get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS tickets (
                    id TEXT PRIMARY KEY,
                    type TEXT NOT NULL,
                    title TEXT NOT NULL,
                    status TEXT NOT NULL,
                    target_file TEXT,
                    function_signature TEXT,
                    parameters TEXT,
                    return_type TEXT,
                    dependencies TEXT,
                    related_interfaces TEXT,
                    description TEXT,
                    retry_count INTEGER,
                    max_retries INTEGER,
                    error_log TEXT,
                    llm_output TEXT,
                    git_hash_before TEXT,
                    git_hash_after TEXT,
                    depends_on TEXT,
                    blocks TEXT,
                    epic TEXT,
                    created_at TEXT,
                    started_at TEXT,
                    completed_at TEXT,
                    escalation_note TEXT,
                    human_feedback TEXT
                )
            """)
            conn.commit()

    def _row_to_ticket(self, row) -> Ticket:
        return Ticket(
            id=row[0],
            type=TicketType(row[1]),
            title=row[2],
            status=TicketStatus(row[3]),
            target_file=row[4] or "",
            function_signature=row[5] or "",
            parameters=row[6] or "",
            return_type=row[7] or "",
            dependencies=row[8] or "",
            related_interfaces=row[9] or "",
            description=row[10] or "",
            retry_count=row[11] or 0,
            max_retries=row[12] or 3,
            error_log=row[13] or "",
            llm_output=row[14] or "",
            git_hash_before=row[15] or "",
            git_hash_after=row[16] or "",
            depends_on=json.loads(row[17]) if row[17] else [],
            blocks=json.loads(row[18]) if row[18] else [],
            epic=row[19] or "",
            created_at=row[20],
            started_at=row[21],
            completed_at=row[22],
            escalation_note=row[23] or "",
            human_feedback=row[24] or ""
        )

    def add_ticket(self, ticket: Ticket):
        with self._get_connection() as conn:
            conn.execute("""
                INSERT INTO tickets (
                    id, type, title, status, target_file, function_signature, parameters,
                    return_type, dependencies, related_interfaces, description,
                    retry_count, max_retries, error_log, llm_output, git_hash_before,
                    git_hash_after, depends_on, blocks, epic, created_at, started_at,
                    completed_at, escalation_note, human_feedback
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                ticket.id, ticket.type.value, ticket.title, ticket.status.value, ticket.target_file,
                ticket.function_signature, ticket.parameters, ticket.return_type, ticket.dependencies,
                ticket.related_interfaces, ticket.description, ticket.retry_count, ticket.max_retries,
                ticket.error_log, ticket.llm_output, ticket.git_hash_before, ticket.git_hash_after,
                json.dumps(ticket.depends_on), json.dumps(ticket.blocks), ticket.epic,
                ticket.created_at, ticket.started_at, ticket.completed_at,
                ticket.escalation_note, ticket.human_feedback
            ))
            conn.commit()

    def get_ticket(self, ticket_id: str) -> Optional[Ticket]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM tickets WHERE id = ?", (ticket_id,))
            row = cursor.fetchone()
            if row:
                return self._row_to_ticket(row)
        return None

    def update_ticket(self, ticket: Ticket):
        with self._get_connection() as conn:
            conn.execute("""
                UPDATE tickets SET
                    type = ?, title = ?, status = ?, target_file = ?, function_signature = ?,
                    parameters = ?, return_type = ?, dependencies = ?, related_interfaces = ?,
                    description = ?, retry_count = ?, max_retries = ?, error_log = ?,
                    llm_output = ?, git_hash_before = ?, git_hash_after = ?, depends_on = ?,
                    blocks = ?, epic = ?, started_at = ?, completed_at = ?,
                    escalation_note = ?, human_feedback = ?
                WHERE id = ?
            """, (
                ticket.type.value, ticket.title, ticket.status.value, ticket.target_file,
                ticket.function_signature, ticket.parameters, ticket.return_type, ticket.dependencies,
                ticket.related_interfaces, ticket.description, ticket.retry_count, ticket.max_retries,
                ticket.error_log, ticket.llm_output, ticket.git_hash_before, ticket.git_hash_after,
                json.dumps(ticket.depends_on), json.dumps(ticket.blocks), ticket.epic,
                ticket.started_at, ticket.completed_at, ticket.escalation_note,
                ticket.human_feedback, ticket.id
            ))
            conn.commit()

    def list_tickets(self) -> List[Ticket]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM tickets")
            rows = cursor.fetchall()
            return [self._row_to_ticket(r) for r in rows]

    def get_next_runnable_ticket(self) -> Optional[Ticket]:
        """
        Returns the next ticket that can be executed.
        Runnable conditions:
        - Status is BACKLOG or FAILED
        - retry_count < max_retries
        - All parent tickets in depends_on list are status DONE.
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            # Fetch all candidate tickets
            cursor.execute("""
                SELECT * FROM tickets 
                WHERE status IN ('backlog', 'failed')
                ORDER BY created_at ASC
            """)
            candidates = [self._row_to_ticket(r) for r in cursor.fetchall()]

            if not candidates:
                return None

            # Get statuses of all tickets to resolve dependencies
            cursor.execute("SELECT id, status FROM tickets")
            status_map = {r[0]: r[1] for r in cursor.fetchall()}

            for ticket in candidates:
                if ticket.retry_count >= ticket.max_retries:
                    continue
                # Check if all dependencies are DONE
                runnable = True
                for dep in ticket.depends_on:
                    dep_status = status_map.get(dep)
                    if dep_status != "done":
                        runnable = False
                        break
                if runnable:
                    return ticket

            return None
