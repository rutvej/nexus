import sqlite3
import json
from typing import List, Optional
from nexus.tickets.models import Ticket, TicketType, TicketStatus

class TicketQueue:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.conn = sqlite3.connect(self.db_path)
        if self.db_path != ":memory:":
            try:
                self.conn.execute("PRAGMA journal_mode=WAL")
            except sqlite3.OperationalError:
                pass
        self._init_db()

    def _get_conn(self):
        return self.conn

    def _init_db(self):
        with self._get_conn() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS tickets (
                    id TEXT PRIMARY KEY,
                    type TEXT NOT NULL,
                    title TEXT NOT NULL,
                    status TEXT NOT NULL,
                    target_file TEXT NOT NULL,
                    function_signature TEXT,
                    parameters TEXT,
                    return_type TEXT,
                    dependencies TEXT,
                    related_interfaces TEXT,
                    description TEXT,
                    retry_count INTEGER DEFAULT 0,
                    max_retries INTEGER DEFAULT 3,
                    error_log TEXT,
                    llm_output TEXT,
                    git_hash_before TEXT,
                    git_hash_after TEXT,
                    depends_on TEXT,
                    blocks TEXT,
                    epic TEXT,
                    escalation_note TEXT,
                    human_feedback TEXT
                )
            """)
            conn.commit()

    def add_ticket(self, t: Ticket):
        with self._get_conn() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO tickets (
                    id, type, title, status, target_file, function_signature,
                    parameters, return_type, dependencies, related_interfaces,
                    description, retry_count, max_retries, error_log, llm_output,
                    git_hash_before, git_hash_after, depends_on, blocks, epic,
                    escalation_note, human_feedback
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    t.id, t.type.value, t.title, t.status.value, t.target_file,
                    t.function_signature, t.parameters, t.return_type, t.dependencies,
                    t.related_interfaces, t.description, t.retry_count, t.max_retries,
                    t.error_log, t.llm_output, t.git_hash_before, t.git_hash_after,
                    json.dumps(t.depends_on), json.dumps(t.blocks), t.epic,
                    t.escalation_note, t.human_feedback
                )
            )
            conn.commit()

    def update_ticket(self, t: Ticket):
        self.add_ticket(t)

    def get_ticket(self, ticket_id: str) -> Optional[Ticket]:
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM tickets WHERE id = ?", (ticket_id,))
            row = cursor.fetchone()
            if not row:
                return None
            return self._row_to_ticket(row)

    def _row_to_ticket(self, row) -> Ticket:
        return Ticket(
            id=row[0],
            type=TicketType(row[1]),
            title=row[2],
            status=TicketStatus(row[3]),
            target_file=row[4],
            function_signature=row[5] or "",
            parameters=row[6] or "",
            return_type=row[7] or "",
            dependencies=row[8] or "",
            related_interfaces=row[9] or "",
            description=row[10] or "",
            retry_count=row[11],
            max_retries=row[12],
            error_log=row[13] or "",
            llm_output=row[14] or "",
            git_hash_before=row[15] or "",
            git_hash_after=row[16] or "",
            depends_on=json.loads(row[17] or "[]"),
            blocks=json.loads(row[18] or "[]"),
            epic=row[19] or "Epic",
            escalation_note=row[20] or "",
            human_feedback=row[21] or ""
        )

    def list_all(self) -> List[Ticket]:
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM tickets")
            rows = cursor.fetchall()
            return [self._row_to_ticket(r) for r in rows]

    def next_ready(self) -> Optional[Ticket]:
        """
        Picks the next runnable ticket (status backlog/failed, and all depends_on tickets are DONE).
        """
        all_tickets = self.list_all()
        done_ids = {t.id for t in all_tickets if t.status == TicketStatus.DONE}
        
        for t in all_tickets:
            if t.status in (TicketStatus.BACKLOG, TicketStatus.FAILED):
                # Check if all dependencies are DONE
                if all(dep_id in done_ids for dep_id in t.depends_on):
                    return t
        return None

    def recent_history(self) -> List[Ticket]:
        with self._get_conn() as conn:
            cursor = conn.cursor()
            # Order not strictly defined, we can return all tickets sorted by status transitions or just all
            cursor.execute("SELECT * FROM tickets")
            rows = cursor.fetchall()
            return [self._row_to_ticket(r) for r in rows]
