# server/replication/replicator.py
import grpc
import threading
import time
from common import utils
from config import config
from proto import replication_pb2
from proto import replication_pb2_grpc
from proto import payment_pb2
from proto import payment_pb2_grpc

class Replicator:
    """
    Replicator sends transaction entries to peers using ReplicationService.
    """

    def __init__(self, peers=None):
        self.peers = peers if peers is not None else dict(config.PEER_NODES)
        self.lock = threading.Lock()

    def push_transaction(self, entry):
        """
        Push a single transaction (dictionary) to all peers (best-effort).
        """
        tx = payment_pb2.Transaction(
            user_id=entry["user_id"],
            amount=entry["amount"],
            status=entry["status"],
            timestamp=entry["timestamp"]
        )
        req = replication_pb2.ReplicationRequest(transactions=[tx], source_node=config.NODE_ID)
        errors = []
        for pid, addr in self.peers.items():
            # don't send to self
            if pid == config.NODE_ID:
                continue
            try:
                with grpc.insecure_channel(addr) as channel:
                    stub = replication_pb2_grpc.ReplicationServiceStub(channel)
                    resp = stub.ReplicateLedger(req, timeout=config.RPC_TIMEOUT)
                    utils.log_event(f"[REPLICATOR] Sent tx {entry['tx_id']} to {pid}: {resp.status}")
            except Exception as e:
                errors.append((pid, str(e)))
                utils.log_event(f"[REPLICATOR] Error sending to {pid}: {e}")

        if errors:
            utils.log_event(f"[REPLICATOR] push_transaction had errors: {errors}")

    def recover_from_peers(self, merge_callback):
        """
        Pull full ledger history from peers and merge using provided callback.
        merge_callback(peer_id, transactions) should return number of applied entries.
        """
        recovered = 0
        for pid, addr in self.peers.items():
            if pid == config.NODE_ID:
                continue
            try:
                with grpc.insecure_channel(addr) as channel:
                    stub = payment_pb2_grpc.PaymentServiceStub(channel)
                    response = stub.GetHistory(payment_pb2.HistoryRequest(user_id=""), timeout=config.RPC_TIMEOUT)
                    recovered += merge_callback(pid, response.transactions)
            except Exception as e:
                utils.log_event(f"[REPLICATOR] Failed to pull ledger from {pid}: {e}")
        return recovered
