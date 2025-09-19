# /server/time_sync/vector_clock.py

class VectorClock:
    def __init__(self, node_id: str, all_nodes: list):
        self.node_id = node_id
        self.clock = {nid: 0 for nid in all_nodes}

    def tick(self):
        """Increment local node counter"""
        self.clock[self.node_id] += 1

    def update(self, received_clock: dict):
        """
        Merge a received vector clock with local clock
        """
        for node, counter in received_clock.items():
            self.clock[node] = max(self.clock.get(node, 0), counter)
        # increment local after merge
        self.tick()

    def get_time(self):
        """Return a copy of the current vector clock"""
        return dict(self.clock)


# Example usage
if __name__ == "__main__":
    nodes = ["node1", "node2", "node3"]
    vc = VectorClock(node_id="node1", all_nodes=nodes)
    print("Initial:", vc.get_time())
    vc.tick()
    print("After local event:", vc.get_time())
    vc.update({"node1": 1, "node2": 3, "node3": 2})
    print("After receiving remote clock:", vc.get_time())
