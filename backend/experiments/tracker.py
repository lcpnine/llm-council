"""SQLite-based experiment tracker."""

import sqlite3
import json
import os
from pathlib import Path
from typing import List, Dict, Optional

DB_PATH = os.path.join("data", "experiments.db")


def _ensure_db():
    """Create the database and tables if they don't exist."""
    Path(os.path.dirname(DB_PATH)).mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS experiments (
            id TEXT PRIMARY KEY,
            timestamp TEXT,
            model TEXT,
            prompt_version TEXT,
            dataset TEXT,
            n_samples INTEGER,
            n_stages INTEGER,
            status TEXT DEFAULT 'running',
            accuracy REAL,
            f1_macro REAL,
            maybe_recall REAL,
            full_metrics TEXT,
            config TEXT,
            total_tokens INTEGER,
            notes TEXT DEFAULT '',
            tags TEXT DEFAULT '[]',
            progress TEXT
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            experiment_id TEXT,
            question_id TEXT,
            predicted TEXT,
            gold TEXT,
            correct INTEGER,
            debate_log TEXT,
            token_usage TEXT,
            FOREIGN KEY (experiment_id) REFERENCES experiments(id)
        )
    """)
    conn.commit()
    conn.close()
    _migrate_db()


def _migrate_db():
    """Add new columns to existing tables if they don't exist."""
    conn = sqlite3.connect(DB_PATH)
    try:
        # Check existing columns on experiments
        cols = {row[1] for row in conn.execute("PRAGMA table_info(experiments)").fetchall()}
        migrations = {
            "total_tokens": "ALTER TABLE experiments ADD COLUMN total_tokens INTEGER",
            "notes": "ALTER TABLE experiments ADD COLUMN notes TEXT DEFAULT ''",
            "tags": "ALTER TABLE experiments ADD COLUMN tags TEXT DEFAULT '[]'",
            "progress": "ALTER TABLE experiments ADD COLUMN progress TEXT",
        }
        for col, sql in migrations.items():
            if col not in cols:
                conn.execute(sql)

        # Check existing columns on results
        result_cols = {row[1] for row in conn.execute("PRAGMA table_info(results)").fetchall()}
        if "token_usage" not in result_cols:
            conn.execute("ALTER TABLE results ADD COLUMN token_usage TEXT")

        conn.commit()
    finally:
        conn.close()


def save_experiment(experiment: Dict) -> None:
    """Save a complete experiment (metadata + per-question results) to the DB."""
    _ensure_db()
    conn = sqlite3.connect(DB_PATH)
    try:
        metrics = experiment.get("metrics", {})
        token_usage = experiment.get("total_token_usage", {})
        total_tokens = token_usage.get("total_tokens", 0) if token_usage else 0

        conn.execute(
            """INSERT OR REPLACE INTO experiments
               (id, timestamp, model, prompt_version, dataset, n_samples, n_stages,
                status, accuracy, f1_macro, maybe_recall, full_metrics, config, total_tokens)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                experiment["id"],
                experiment.get("timestamp", ""),
                experiment.get("model", ""),
                experiment.get("prompt_version", ""),
                experiment.get("dataset", ""),
                experiment.get("n_samples", 0),
                experiment.get("n_stages", 3),
                experiment.get("status", "completed"),
                metrics.get("accuracy"),
                metrics.get("f1_macro"),
                metrics.get("maybe_recall"),
                json.dumps(metrics),
                json.dumps(experiment.get("config", {})),
                total_tokens,
            ),
        )

        # Delete old results for this experiment (in case of re-run)
        conn.execute("DELETE FROM results WHERE experiment_id = ?", (experiment["id"],))

        for r in experiment.get("results", []):
            conn.execute(
                """INSERT INTO results
                   (experiment_id, question_id, predicted, gold, correct, debate_log, token_usage)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (
                    experiment["id"],
                    r.get("question_id", ""),
                    r.get("predicted", ""),
                    r.get("gold", ""),
                    r.get("correct", 0),
                    json.dumps(r.get("debate_log", {})),
                    json.dumps(r.get("token_usage", {})),
                ),
            )

        conn.commit()
    finally:
        conn.close()


def mark_experiment_running(experiment_id: str, config: Dict) -> None:
    """Insert a placeholder experiment row with status='running'."""
    _ensure_db()
    conn = sqlite3.connect(DB_PATH)
    try:
        from datetime import datetime
        conn.execute(
            """INSERT OR REPLACE INTO experiments
               (id, timestamp, model, prompt_version, dataset, n_samples, n_stages,
                status, config)
               VALUES (?, ?, ?, ?, ?, ?, ?, 'running', ?)""",
            (
                experiment_id,
                datetime.utcnow().isoformat(),
                config.get("model", ""),
                config.get("prompt_version", ""),
                config.get("dataset", ""),
                config.get("n_samples", 0),
                config.get("n_stages", 3),
                json.dumps(config),
            ),
        )
        conn.commit()
    finally:
        conn.close()


def update_progress(experiment_id: str, current: int, total: int) -> None:
    """Update progress for a running experiment."""
    _ensure_db()
    conn = sqlite3.connect(DB_PATH)
    try:
        progress = json.dumps({"current": current, "total": total})
        conn.execute(
            "UPDATE experiments SET progress = ? WHERE id = ?",
            (progress, experiment_id),
        )
        conn.commit()
    finally:
        conn.close()


def update_notes(experiment_id: str, notes: str) -> None:
    """Update notes for an experiment."""
    _ensure_db()
    conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute(
            "UPDATE experiments SET notes = ? WHERE id = ?",
            (notes, experiment_id),
        )
        conn.commit()
    finally:
        conn.close()


def update_tags(experiment_id: str, tags: List[str]) -> None:
    """Update tags for an experiment."""
    _ensure_db()
    conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute(
            "UPDATE experiments SET tags = ? WHERE id = ?",
            (json.dumps(tags), experiment_id),
        )
        conn.commit()
    finally:
        conn.close()


def delete_experiment(experiment_id: str) -> bool:
    """Delete an experiment and its results. Returns True if found."""
    _ensure_db()
    conn = sqlite3.connect(DB_PATH)
    try:
        cursor = conn.execute("DELETE FROM experiments WHERE id = ?", (experiment_id,))
        conn.execute("DELETE FROM results WHERE experiment_id = ?", (experiment_id,))
        conn.commit()
        return cursor.rowcount > 0
    finally:
        conn.close()


def get_all_experiments() -> List[Dict]:
    """Return all experiments (summary, no per-question results)."""
    _ensure_db()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            "SELECT * FROM experiments ORDER BY timestamp DESC"
        ).fetchall()
        result = []
        for r in rows:
            exp = {
                "id": r["id"],
                "timestamp": r["timestamp"],
                "model": r["model"],
                "prompt_version": r["prompt_version"],
                "dataset": r["dataset"],
                "n_samples": r["n_samples"],
                "n_stages": r["n_stages"],
                "status": r["status"],
                "accuracy": r["accuracy"],
                "f1_macro": r["f1_macro"],
                "maybe_recall": r["maybe_recall"],
                "full_metrics": json.loads(r["full_metrics"]) if r["full_metrics"] else None,
                "total_tokens": r["total_tokens"],
                "notes": r["notes"] or "",
                "tags": json.loads(r["tags"]) if r["tags"] else [],
                "progress": json.loads(r["progress"]) if r["progress"] else None,
            }
            result.append(exp)
        return result
    finally:
        conn.close()


def get_experiment(experiment_id: str) -> Optional[Dict]:
    """Return a single experiment with full metrics."""
    _ensure_db()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        row = conn.execute(
            "SELECT * FROM experiments WHERE id = ?", (experiment_id,)
        ).fetchone()
        if row is None:
            return None
        return {
            "id": row["id"],
            "timestamp": row["timestamp"],
            "model": row["model"],
            "prompt_version": row["prompt_version"],
            "dataset": row["dataset"],
            "n_samples": row["n_samples"],
            "n_stages": row["n_stages"],
            "status": row["status"],
            "accuracy": row["accuracy"],
            "f1_macro": row["f1_macro"],
            "maybe_recall": row["maybe_recall"],
            "full_metrics": json.loads(row["full_metrics"]) if row["full_metrics"] else None,
            "config": json.loads(row["config"]) if row["config"] else None,
            "total_tokens": row["total_tokens"],
            "notes": row["notes"] or "",
            "tags": json.loads(row["tags"]) if row["tags"] else [],
            "progress": json.loads(row["progress"]) if row["progress"] else None,
        }
    finally:
        conn.close()


def get_results(experiment_id: str) -> List[Dict]:
    """Return per-question results for an experiment."""
    _ensure_db()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            "SELECT * FROM results WHERE experiment_id = ? ORDER BY id",
            (experiment_id,),
        ).fetchall()
        return [
            {
                "question_id": r["question_id"],
                "predicted": r["predicted"],
                "gold": r["gold"],
                "correct": r["correct"],
                "debate_log": json.loads(r["debate_log"]) if r["debate_log"] else {},
                "token_usage": json.loads(r["token_usage"]) if r["token_usage"] else {},
            }
            for r in rows
        ]
    finally:
        conn.close()


def compare_experiments(experiment_ids: List[str]) -> Dict:
    """Load multiple experiments with their results for comparison."""
    experiments = []
    for eid in experiment_ids:
        exp = get_experiment(eid)
        if exp:
            exp["results"] = get_results(eid)
            experiments.append(exp)
    return {"experiments": experiments}
