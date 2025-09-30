# server/node/failover.py
import config
from common import utils

class FailoverManager:
    """
    Simple failover manager.
    - Uses heartbeat status information (from HeartbeatMonitor) to choose a live node.
    - If leader is known and down, will indicate a different node to use.
    """

    def __init__(self, heartbeat_monitor, consensus_module):
        """
        heartbeat_monitor: instance of HeartbeatMonitor
        consensus_module: object exposing get_leader() method
        """
        self.hb = heartbeat_monitor
        self.consensus = consensus_module

    def choose_node_for_client(self):
        """
        Choose a node for a client to use.
        Prefer the current leader if alive, otherwise fall back to the lowest-latency live peer or self.
        Returns a tuple (node_id, address_str) or None.
        """
        leader = None
        try:
            leader = self.consensus.get_leader()
        except Exception:
            leader = None

        peers = dict(config.PEER_NODES)
        # include self in candidate list
        peers[config.NODE_ID] = f"{config.SERVER_HOST}:{config.SERVER_PORT}"

        live = set(self.hb.get_live_peers())
        # If leader is known and live, return it
        if leader and leader in peers and (leader in live or leader == config.NODE_ID):
            return leader, peers[leader]

        # else choose any live peer (prefer others)
        ranked_live = sorted(
            list(live),
            key=lambda pid: self.hb.get_latency_ms(pid) if self.hb.get_latency_ms(pid) is not None else float("inf")
        )
        for pid in ranked_live:
            if pid in peers:
                return pid, peers[pid]

        # fallback to self
        return config.NODE_ID, f"{config.SERVER_HOST}:{config.SERVER_PORT}"
