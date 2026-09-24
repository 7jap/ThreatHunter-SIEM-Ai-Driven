import sqlite3
import json
import logging
from pathlib import Path
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

class SQLiteQueue:
    def __init__(self, db_path: str, max_size: int = 100000):
        self.db_path = Path(db_path)
        self.max_size = max_size
        self._init_db()

    def _init_db(self):
        try:
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            with sqlite3.connect(self.db_path) as conn:
                # Use WAL mode for better concurrency and crash resistance
                conn.execute("PRAGMA journal_mode=WAL;")
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS event_queue (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        event_id TEXT UNIQUE NOT NULL,
                        timestamp TEXT NOT NULL,
                        payload TEXT NOT NULL
                    )
                """)
                # Index for quick retrieval
                conn.execute("CREATE INDEX IF NOT EXISTS idx_timestamp ON event_queue(timestamp);")
        except Exception as e:
            logger.critical(f"Failed to initialize SQLite queue at {self.db_path}: {e}")
            raise

    def enqueue(self, event_id: str, timestamp: str, payload: dict) -> bool:
        """Add an event to the local queue."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Capacity limit check
                cursor = conn.execute("SELECT COUNT(*) FROM event_queue")
                count = cursor.fetchone()[0]
                if count >= self.max_size:
                    logger.warning(f"Queue size limit reached ({self.max_size}). Dropping oldest events.")
                    # Delete the oldest 10% to make room
                    delete_count = max(1, int(self.max_size * 0.1))
                    conn.execute(f"""
                        DELETE FROM event_queue 
                        WHERE id IN (
                            SELECT id FROM event_queue ORDER BY id ASC LIMIT {delete_count}
                        )
                    """)
                
                conn.execute(
                    "INSERT OR IGNORE INTO event_queue (event_id, timestamp, payload) VALUES (?, ?, ?)",
                    (event_id, timestamp, json.dumps(payload))
                )
            return True
        except Exception as e:
            logger.error(f"Failed to enqueue event {event_id}: {e}")
            return False

    def dequeue_batch(self, batch_size: int = 100) -> List[Dict]:
        """Fetch a batch of events to send to the server. Does NOT delete them."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute(
                    "SELECT id, event_id, timestamp, payload FROM event_queue ORDER BY id ASC LIMIT ?",
                    (batch_size,)
                )
                rows = cursor.fetchall()
                
                events = []
                for row in rows:
                    events.append({
                        "internal_id": row["id"],
                        "event_id": row["event_id"],
                        "timestamp": row["timestamp"],
                        "payload": json.loads(row["payload"])
                    })
                return events
        except Exception as e:
            logger.error(f"Failed to dequeue events: {e}")
            return []

    def acknowledge(self, event_ids: List[str]):
        """Delete events from the queue ONLY after server acknowledges them."""
        if not event_ids:
            return
            
        try:
            with sqlite3.connect(self.db_path) as conn:
                placeholders = ",".join("?" for _ in event_ids)
                conn.execute(
                    f"DELETE FROM event_queue WHERE event_id IN ({placeholders})",
                    event_ids
                )
                logger.debug(f"Acknowledged and removed {len(event_ids)} events from queue.")
        except Exception as e:
            logger.error(f"Failed to acknowledge events: {e}")

    def get_size(self) -> int:
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("SELECT COUNT(*) FROM event_queue")
                return cursor.fetchone()[0]
        except Exception as e:
            logger.error(f"Failed to get queue size: {e}")
            return 0
