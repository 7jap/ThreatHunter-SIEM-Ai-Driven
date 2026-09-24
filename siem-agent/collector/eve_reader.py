import os
import json
import time
import uuid
import logging
from typing import Optional

logger = logging.getLogger(__name__)

class EveReader:
    def __init__(self, log_path: str, queue, agent_id: str):
        self.log_path = log_path
        self.queue = queue
        self.agent_id = agent_id
        # We store the bookmark in the same directory as the queue
        self.bookmark_path = os.path.join(os.path.dirname(queue.db_path), "eve_bookmark.json")
        self.inode = None
        self.offset = 0
        self._load_bookmark()

    def _load_bookmark(self):
        if os.path.exists(self.bookmark_path):
            try:
                with open(self.bookmark_path, "r") as f:
                    data = json.load(f)
                    self.inode = data.get("inode")
                    self.offset = data.get("offset", 0)
                logger.info(f"Loaded bookmark: inode={self.inode}, offset={self.offset}")
            except Exception as e:
                logger.error(f"Failed to load bookmark: {e}")
                self.offset = 0

    def _save_bookmark(self):
        try:
            with open(self.bookmark_path, "w") as f:
                json.dump({"inode": self.inode, "offset": self.offset}, f)
        except Exception as e:
            logger.error(f"Failed to save bookmark: {e}")

    def read_new_events(self):
        """Reads new events from eve.json and queues them."""
        if not self.log_path or not os.path.exists(self.log_path):
            logger.debug(f"Eve log file not found at {self.log_path}")
            return

        try:
            stat = os.stat(self.log_path)
            current_inode = stat.st_ino
            
            # File rotation detected
            if self.inode and self.inode != current_inode:
                logger.info("Log rotation detected. Resetting offset.")
                self.offset = 0
                
            self.inode = current_inode
            
            # File was truncated
            if stat.st_size < self.offset:
                logger.info("Log file truncated. Resetting offset.")
                self.offset = 0

            with open(self.log_path, "r") as f:
                f.seek(self.offset)
                
                events_processed = 0
                for line in f:
                    if not line.strip():
                        continue
                        
                    try:
                        event = json.loads(line)
                        self._process_event(event)
                        events_processed += 1
                    except json.JSONDecodeError:
                        logger.warning("Malformed JSON in eve.json. Skipping line.")
                        continue
                        
                # Update offset after reading
                new_offset = f.tell()
                if new_offset != self.offset:
                    self.offset = new_offset
                    self._save_bookmark()
                    
                if events_processed > 0:
                    logger.debug(f"Processed {events_processed} new events.")
                    
        except Exception as e:
            logger.error(f"Error reading eve.json: {e}")

    def _process_event(self, event: dict):
        # Validate schema minimally
        if "timestamp" not in event or "event_type" not in event:
            return
            
        # ONLY send Alerts to the Server to save bandwidth and storage
        if event["event_type"] != "alert":
            return
            
        # Add tracking fields
        event_id = str(uuid.uuid4())
        timestamp = event["timestamp"]
        event["_agent_id"] = self.agent_id
        event["_event_id"] = event_id
        
        # Enqueue for secure transport
        self.queue.enqueue(event_id, timestamp, event)
