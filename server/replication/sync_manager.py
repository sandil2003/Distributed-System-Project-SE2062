# server/replication/sync_manager.py
import threading
import json
import os
from common import utils
from config import config

from proto import replication_pb2
from proto import replication_pb2_grpc
from proto import payment_pb2
from proto import payment_pb2_grpc

LEDGER_FILE = config.LEDGER_FILE

class ReplicationService(replication_pb2_grpc.ReplicationServiceServicer):
    """
    Receives replication requests from peers and applies transactions to local ledger.
    """

    def __init__(self, deduplicator=None):
        self.ledger_lock = threading.Lock()
        if not os.path.exists(LEDGER_FILE):
            with open(LEDGER_FILE, "w") as f:
                json.dump([], f)
        self.dedup = deduplicator

    def _append_if_not_exists(self, tx):
        with self.ledger_lock:
            with open(LEDGER_FILE, "r+") as f:
                try:
                    ledger = json.load(f)
                except Exception:
                    ledger = []
                # dedup by tx fields (best-effort)
                exists = any(entry.get("timestamp") == tx.timestamp and entry.get("user_id") == tx.user_id and entry.get("amount") == tx.amount for entry in ledger)
                if not exists:
                    new = {
                        "tx_id": f"rep-{tx.timestamp}-{tx.user_id}",
                        "user_id": tx.user_id,
                        "amount": tx.amount,
                        "status": tx.status,
                        "timestamp": tx.timestamp,
                        "source": "replication"
                    }
                    ledger.append(new)
                    f.seek(0)
                    json.dump(ledger, f, indent=2)
                    f.truncate()
                    utils.log_event(f"[REPLICATION] Appended replicated tx for {tx.user_id} at {tx.timestamp}")
                    return True
                else:
                    utils.log_event(f"[REPLICATION] Duplicate detected for {tx.user_id} @ {tx.timestamp}")
                    return False

    def ReplicateLedger(self, request, context):
        try:
            for tx in request.transactions:
                self._append_if_not_exists(tx)
            return replication_pb2.ReplicationResponse(status="OK", message="Applied")
        except Exception as e:
            utils.log_event(f"[REPLICATION] Error: {e}")
            return replication_pb2.ReplicationResponse(status="FAILED", message=str(e))
