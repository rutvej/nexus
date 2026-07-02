import sqlite3
import json
from datetime import datetime
from typing import Dict, Any, List, Optional

DB_PATH = "/home/rutvej/nexus_eval/nexus_eval.db"

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Create benchmark_runs table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS benchmark_runs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        run_id TEXT NOT NULL UNIQUE,
        timestamp TEXT NOT NULL,
        benchmark_version TEXT NOT NULL
    )
    """)
    
    # Create benchmark_results table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS benchmark_results (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        run_id TEXT NOT NULL,
        task_id TEXT NOT NULL,
        model_name TEXT NOT NULL,
        category TEXT NOT NULL,
        success INTEGER NOT NULL,          -- 0 or 1
        syntax_correct INTEGER,            -- 0 or 1
        compile_success INTEGER,           -- 0 or 1
        test_success INTEGER,              -- 0 or 1
        tool_accuracy REAL,                -- 0.0 - 1.0
        latency_ms REAL NOT NULL,
        tokens_prompt INTEGER NOT NULL,
        tokens_generated INTEGER NOT NULL,
        memory_mb REAL,
        raw_output TEXT,
        timestamp TEXT NOT NULL,
        FOREIGN KEY (run_id) REFERENCES benchmark_runs(run_id)
    )
    """)
    
    # Create model_scores table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS model_scores (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        model_name TEXT NOT NULL,
        task_type TEXT NOT NULL,
        score REAL NOT NULL,               -- Composite score 0.0 - 1.0
        accuracy REAL,
        speed REAL,
        efficiency REAL,
        reliability REAL,
        sample_count INTEGER NOT NULL,     -- Number of runs
        last_updated TEXT NOT NULL,
        UNIQUE(model_name, task_type)
    )
    """)
    
    # Indexes
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_results_model ON benchmark_results(model_name)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_results_category ON benchmark_results(category)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_scores_model ON model_scores(model_name)")
    
    conn.commit()
    conn.close()

def record_run(run_id: str, version: str = "1.0.0") -> None:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO benchmark_runs (run_id, timestamp, benchmark_version) VALUES (?, ?, ?)",
        (run_id, datetime.utcnow().isoformat(), version)
    )
    conn.commit()
    conn.close()

def record_result(run_id: str, result_data: Dict[str, Any]) -> None:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO benchmark_results (
            run_id, task_id, model_name, category, success,
            syntax_correct, compile_success, test_success, tool_accuracy,
            latency_ms, tokens_prompt, tokens_generated, raw_output, timestamp
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        run_id,
        result_data["task_id"],
        result_data["model_name"],
        result_data["category"],
        1 if result_data["success"] else 0,
        1 if result_data.get("syntax_correct") else 0,
        1 if result_data.get("compile_success") else 0,
        1 if result_data.get("test_success") else 0,
        result_data.get("tool_accuracy", 0.0),
        result_data["latency_ms"],
        result_data["tokens_prompt"],
        result_data["tokens_generated"],
        result_data["raw_output"],
        datetime.utcnow().isoformat()
    ))
    conn.commit()
    conn.close()

def update_model_score(model_name: str, task_type: str, success: bool, latency_ms: float, tokens_gen: int, alpha: float = 0.2) -> None:
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Fetch existing score
    cursor.execute(
        "SELECT score, accuracy, speed, efficiency, reliability, sample_count FROM model_scores WHERE model_name = ? AND task_type = ?",
        (model_name, task_type)
    )
    row = cursor.fetchone()
    
    # Calculate new values
    new_accuracy = 1.0 if success else 0.0
    
    # Normalize speed (latency): assume 5000ms is worst case, 100ms is best
    norm_speed = max(0.0, min(1.0, 1.0 - (latency_ms - 100) / 4900))
    
    # Normalize efficiency: tokens per second or inverse of tokens gen (assume fewer tokens for same success is better)
    # Let's say speed (tokens/sec) is the efficiency metric here
    tokens_per_sec = (tokens_gen / (latency_ms / 1000.0)) if latency_ms > 0 else 0.0
    # Normalize tokens/sec: assume 50 tokens/sec is max, 0 is min
    norm_efficiency = max(0.0, min(1.0, tokens_per_sec / 50.0))
    
    new_reliability = 1.0 if success else 0.0 # simple binary reliability for now
    
    if row:
        curr_score = row["score"]
        curr_accuracy = row["accuracy"]
        curr_speed = row["speed"]
        curr_efficiency = row["efficiency"]
        curr_reliability = row["reliability"]
        sample_count = row["sample_count"] + 1
        
        # Exponential Moving Average (EMA)
        updated_accuracy = alpha * new_accuracy + (1 - alpha) * curr_accuracy
        updated_speed = alpha * norm_speed + (1 - alpha) * curr_speed
        updated_efficiency = alpha * norm_efficiency + (1 - alpha) * curr_efficiency
        updated_reliability = alpha * new_reliability + (1 - alpha) * curr_reliability
    else:
        updated_accuracy = new_accuracy
        updated_speed = norm_speed
        updated_efficiency = norm_efficiency
        updated_reliability = new_reliability
        sample_count = 1
        
    # Composite score formula from Section 11.3:
    # score = accuracy * 0.50 + speed * 0.20 + efficiency * 0.10 + reliability * 0.20
    composite_score = (
        updated_accuracy * 0.50 +
        updated_speed * 0.20 +
        updated_efficiency * 0.10 +
        updated_reliability * 0.20
    )
    
    cursor.execute("""
        INSERT INTO model_scores (model_name, task_type, score, accuracy, speed, efficiency, reliability, sample_count, last_updated)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(model_name, task_type) DO UPDATE SET
            score = excluded.score,
            accuracy = excluded.accuracy,
            speed = excluded.speed,
            efficiency = excluded.efficiency,
            reliability = excluded.reliability,
            sample_count = excluded.sample_count,
            last_updated = excluded.last_updated
    """, (
        model_name, task_type, composite_score, updated_accuracy, updated_speed, updated_efficiency, updated_reliability,
        sample_count, datetime.utcnow().isoformat()
    ))
    
    conn.commit()
    conn.close()

def get_all_scores() -> List[Dict[str, Any]]:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM model_scores ORDER BY model_name, task_type")
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]
