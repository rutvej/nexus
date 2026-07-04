#!/bin/bash
# check_tickets.sh - Query ticket statuses from the Nexus session database

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DB_PATH="$SCRIPT_DIR/data/session.db"

if [ ! -f "$DB_PATH" ]; then
    echo "❌ No session.db found at $DB_PATH. Run the experiment first."
    exit 1
fi

echo ""
echo "=== Nexus Ticket Status ==="
python3 << EOF
import sqlite3
conn = sqlite3.connect("$DB_PATH")
cursor = conn.cursor()

# Summary counts
cursor.execute("SELECT status, COUNT(*) FROM tickets GROUP BY status")
rows = cursor.fetchall()
total = sum(r[1] for r in rows)
print(f"\n📊 Total tickets: {total}")
for status, count in rows:
    emoji = {"done": "✅", "escalated": "🔴", "in_progress": "🔄", "backlog": "⏳", "failed": "❌"}.get(status, "❓")
    print(f"  {emoji} {status.upper()}: {count}")

# Ticket detail table
print("\n--- Ticket Details ---")
cursor.execute("SELECT id, type, title, status, retry_count FROM tickets ORDER BY id")
rows = cursor.fetchall()
print(f"{'ID':<20} {'TYPE':<15} {'TITLE':<35} {'STATUS':<12} {'RETRIES':<8}")
print("-" * 95)
for row in rows:
    tid, ttype, title, status, retries = row
    emoji = {"done": "✅", "escalated": "🔴", "in_progress": "🔄", "backlog": "⏳", "failed": "❌"}.get(status, "❓")
    print(f"{tid:<20} {ttype:<15} {title[:34]:<35} {emoji} {status:<10} {retries:<8}")

# Show error logs for escalated tickets
print("\n--- Error Logs (Escalated Only) ---")
cursor.execute("SELECT id, error_log FROM tickets WHERE status='escalated' ORDER BY id")
rows = cursor.fetchall()
for tid, error_log in rows:
    print(f"\n🔴 {tid}:")
    # Trim error log to first 15 lines
    lines = error_log.strip().splitlines()[:15]
    for line in lines:
        print(f"   {line}")
    if len(error_log.strip().splitlines()) > 15:
        print(f"   ... ({len(error_log.strip().splitlines()) - 15} more lines)")

conn.close()
EOF
