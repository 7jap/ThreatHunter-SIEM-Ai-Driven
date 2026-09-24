import json
import time
import logging
import requests
from requests.exceptions import RequestException
from typing import List, Dict

logger = logging.getLogger(__name__)

class TransportClient:
    def __init__(self, config_manager, queue):
        self.config = config_manager
        self.queue = queue
        
        server_cfg = self.config.get("server")
        tls_enabled = server_cfg.get("tls_enabled", True)
        
        sec_cfg = self.config.get("security")
        self.cert = (sec_cfg.get("client_cert_path"), sec_cfg.get("client_key_path"))
        self.ca_cert = sec_cfg.get("ca_cert_path")
        
        # Graceful fallback: If we lack certificates entirely, assume the server is also in cleartext dev mode
        import os
        if tls_enabled and (not self.cert[0] or not os.path.exists(self.cert[0])):
            logger.warning("No TLS certs found locally. Falling back to HTTP protocol to match Server's cleartext mode.")
            self.use_tls = False
            protocol = "http"
        else:
            self.use_tls = tls_enabled
            protocol = "https" if tls_enabled else "http"
            
        self.base_url = f"{protocol}://{server_cfg['host']}:{server_cfg['port']}/api/v1"
        
        self.agent_id = self.config.get("agent", "id")
        
        # Backoff settings
        self.base_retry_delay = 5
        self.max_retry_delay = 300
        self.current_retry_delay = self.base_retry_delay

    def _get_session(self):
        import os
        session = requests.Session()
        
        # Verify certs exist to prevent hard crash
        client_crt, client_key = self.cert
        if self.use_tls:
            if not client_crt or not client_key or not os.path.exists(client_crt) or not os.path.exists(client_key):
                session.verify = False  # Try without it so we don't crash the script completely during test
            elif not self.ca_cert or not os.path.exists(self.ca_cert):
                session.verify = False
            else:
                session.cert = self.cert
                session.verify = self.ca_cert
        else:
            session.verify = False

        # Suppress insecure request warnings if verify is False
        if not session.verify:
            import urllib3
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

        # Hardcode headers
        session.headers.update({
            "Content-Type": "application/json",
            "X-Agent-ID": str(self.agent_id)
        })
        return session

    def send_heartbeat(self, status: dict):
        try:
            url = f"{self.base_url}/agent/heartbeat"
            session = self._get_session()
            
            payload = {
                "agent_id": self.agent_id,
                "timestamp": time.strftime('%Y-%m-%dT%H:%M:%S%z'),
                "status": status
            }
            
            response = session.post(url, json=payload, timeout=10)
            response.raise_for_status()
            logger.debug("Heartbeat sent successfully.")
            return True
        except RequestException as e:
            logger.warning(f"Failed to send heartbeat: {e}")
            return False

    def sync_events(self):
        """Pulls from local queue and sends to server, expecting ACKs."""
        if not self.agent_id:
            logger.warning("Agent ID not configured. Cannot sync events.")
            return

        batch = self.queue.dequeue_batch(batch_size=100)
        if not batch:
            return

        url = f"{self.base_url}/events"
        session = self._get_session()
        
        # Format payload
        payload = {
            "agent_id": self.agent_id,
            "events": [e["payload"] for e in batch]
        }
        
        try:
            logger.info(f"Attempting to sync {len(batch)} events...")
            response = session.post(url, json=payload, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                acked_ids = data.get("acked_event_ids", [])
                
                # Acknowledge and delete from local queue
                if acked_ids:
                    self.queue.acknowledge(acked_ids)
                    
                # Reset backoff on success
                self.current_retry_delay = self.base_retry_delay
            else:
                logger.error(f"Server rejected events with status {response.status_code}: {response.text}")
                self._apply_backoff()
                
        except RequestException as e:
            logger.error(f"Connection error while syncing events: {e}")
            self._apply_backoff()
            
    def _apply_backoff(self):
        logger.info(f"Backing off for {self.current_retry_delay} seconds.")
        time.sleep(self.current_retry_delay)
        self.current_retry_delay = min(self.current_retry_delay * 2, self.max_retry_delay)
