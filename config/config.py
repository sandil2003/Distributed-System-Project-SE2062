import os
from dotenv import load_dotenv

# Load environment variables from a .env file (optional)
NODE_ENV = os.getenv("NODE_ENV", ".env")
load_dotenv(dotenv_path=NODE_ENV) 

# -------------------------------
# Node configuration
# -------------------------------
NODE_ID = os.getenv("NODE_ID", "node1")  # default node ID
SERVER_HOST = os.getenv("SERVER_HOST", "0.0.0.0")
SERVER_PORT = int(os.getenv("SERVER_PORT", 50051))

# -------------------------------
# Cluster configuration
# -------------------------------
# Example format for .env:
# PEER_NODES=node2:localhost:50052,node3:localhost:50053
PEERS_RAW = os.getenv("PEER_NODES", "")
PEER_NODES = {}

if PEERS_RAW:
    for entry in PEERS_RAW.split(","):
        parts = entry.split(":")
        if len(parts) == 3:
            peer_id, host, port = parts
            PEER_NODES[peer_id] = f"{host}:{port}"

# -------------------------------
# Timeouts & intervals
# -------------------------------
RPC_TIMEOUT = int(os.getenv("RPC_TIMEOUT", 3))  # gRPC request timeout (seconds)
HEARTBEAT_INTERVAL = float(os.getenv("HEARTBEAT_INTERVAL", 1.0))  # Leader heartbeat
ELECTION_TIMEOUT = int(os.getenv("ELECTION_TIMEOUT", 5))  # Election timeout (seconds)
HEARTBEAT_FAILURE_THRESHOLD = int(os.getenv("HEARTBEAT_FAILURE_THRESHOLD", 3))
HEARTBEAT_SLOW_THRESHOLD_MS = float(os.getenv("HEARTBEAT_SLOW_THRESHOLD_MS", 500.0))
HEARTBEAT_LATENCY_ALPHA = float(os.getenv("HEARTBEAT_LATENCY_ALPHA", 0.2))

# -------------------------------
# Ledger / Replication config
# -------------------------------
LEDGER_FILE = os.getenv("LEDGER_FILE", f"ledger_{NODE_ID}.json")  # local ledger file
CONSISTENCY_MODEL = os.getenv("CONSISTENCY_MODEL", "strong")      # "strong" or "eventual"

# -------------------------------
# Consensus persistence config
# -------------------------------
RAFT_STATE_FILE = os.getenv("RAFT_STATE_FILE", f"raft_state_{NODE_ID}.json")

# -------------------------------
# Logging config
# -------------------------------
LOG_FILE = os.getenv("LOG_FILE", f"{NODE_ID}_system.log")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
