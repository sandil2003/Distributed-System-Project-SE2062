# server/node/heartbeat.py
import socket
import threading
import time
from config import config
from common import utils

class HeartbeatMonitor(threading.Thread):
    """
    Adaptive heartbeat monitor that checks whether peer TCP ports are open.
    Tracks rolling latency and only marks peers down after repeated failures.
    """

    def __init__(self, interval=None):
        super().__init__(daemon=True)
        self.interval = interval if interval is not None else config.HEARTBEAT_INTERVAL
        self.peers = dict(config.PEER_NODES)  # copy
        self.running = True
        self.status = {pid: False for pid in self.peers.keys()}
        self.lock = threading.Lock()
        self._last_heartbeat = time.time()
        self.failure_threshold = config.HEARTBEAT_FAILURE_THRESHOLD
        self.slow_threshold_ms = config.HEARTBEAT_SLOW_THRESHOLD_MS
        self.latency_alpha = config.HEARTBEAT_LATENCY_ALPHA
        self.fail_counts = {pid: 0 for pid in self.peers.keys()}
        self.latency_ema = {pid: None for pid in self.peers.keys()}
        self.suspect_flag = {pid: False for pid in self.peers.keys()}

    def check_peer(self, hostport):
        host, port = hostport.split(":")
        start = time.perf_counter()
        try:
            port = int(port)
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(1.0)
            s.connect((host, port))
            latency_ms = (time.perf_counter() - start) * 1000.0
            s.close()
            return True, latency_ms
        except Exception:
            return False, None

    def run_once(self):
        for pid, hostport in self.peers.items():
            alive, latency_ms = self.check_peer(hostport)
            with self.lock:
                prev = self.status.get(pid, False)
                if alive:
                    self.status[pid] = True
                    self.fail_counts[pid] = 0
                    self.suspect_flag[pid] = False
                    if latency_ms is not None:
                        ema = self.latency_ema.get(pid)
                        if ema is None:
                            ema = latency_ms
                        else:
                            ema = self.latency_alpha * latency_ms + (1 - self.latency_alpha) * ema
                        self.latency_ema[pid] = ema
                        if latency_ms > self.slow_threshold_ms:
                            utils.log_event(f"[HEARTBEAT] peer {pid} slow latency={latency_ms:.1f}ms ema={ema:.1f}ms")
                    if not prev:
                        utils.log_event(f"[HEARTBEAT] peer {pid} became ALIVE")
                else:
                    self.fail_counts[pid] = self.fail_counts.get(pid, 0) + 1
                    if self.fail_counts[pid] >= self.failure_threshold:
                        if prev:
                            utils.log_event(f"[HEARTBEAT] peer {pid} became DOWN after {self.fail_counts[pid]} misses")
                        self.status[pid] = False
                        self.suspect_flag[pid] = False
                    else:
                        self.status[pid] = prev
                        if not self.suspect_flag.get(pid, False):
                            utils.log_event(f"[HEARTBEAT] peer {pid} suspected down ({self.fail_counts[pid]} consecutive misses)")
                            self.suspect_flag[pid] = True

    def run(self):
        utils.log_event("[HEARTBEAT] Starting heartbeat monitor")
        while self.running:
            try:
                self.run_once()
            except Exception as e:
                utils.log_event(f"[HEARTBEAT] Error: {e}")
            time.sleep(self.interval)

    def stop(self):
        self.running = False

    def get_live_peers(self):
        with self.lock:
            return [pid for pid, alive in self.status.items() if alive]

    def get_latency_ms(self, pid=None):
        with self.lock:
            if pid is not None:
                return self.latency_ema.get(pid)
            return {peer: self.latency_ema.get(peer) for peer in self.peers.keys()}
