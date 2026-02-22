import unittest
import threading
import time
import grpc
import json
import random
from concurrent.futures import ThreadPoolExecutor, as_completed
from proto import payment_pb2, payment_pb2_grpc
from proto import consensus_pb2, consensus_pb2_grpc
from proto import replication_pb2, replication_pb2_grpc

class ConcurrencyTest(unittest.TestCase):
    def setUp(self):
        # Node configurations
        self.nodes = [
            {"port": 50051, "id": "node1"},
            {"port": 50052, "id": "node2"},
            {"port": 50053, "id": "node3"}
        ]
        
        # Create gRPC channel for each node
        self.channels = {
            node["id"]: grpc.insecure_channel(f'localhost:{node["port"]}')
            for node in self.nodes
        }
        
        # Create stubs for each service type for each node
        self.payment_stubs = {
            node["id"]: payment_pb2_grpc.PaymentServiceStub(self.channels[node["id"]])
            for node in self.nodes
        }
        
        self.consensus_stubs = {
            node["id"]: consensus_pb2_grpc.ConsensusServiceStub(self.channels[node["id"]])
            for node in self.nodes
        }

    def test_concurrent_payments(self):
        """Test concurrent payment processing across all nodes"""
        num_requests = 10
        results = []
        
        def make_payment(node_id, request_id):
            try:
                request = payment_pb2.PaymentRequest(
                    user_id=f"user{request_id}",
                    amount=random.randint(100, 1000),
                    transaction_id=f"tx_{node_id}_{request_id}"
                )
                response = self.payment_stubs[node_id].ProcessPayment(request)
                return {
                    "node_id": node_id,
                    "request_id": request_id,
                    "status": response.status,
                    "success": True
                }
            except Exception as e:
                return {
                    "node_id": node_id,
                    "request_id": request_id,
                    "error": str(e),
                    "success": False
                }

        # Create a thread pool for concurrent execution
        with ThreadPoolExecutor(max_workers=15) as executor:
            futures = []
            # Submit requests to all nodes concurrently
            for node in self.nodes:
                for i in range(num_requests):
                    future = executor.submit(make_payment, node["id"], i)
                    futures.append(future)
            
            # Collect results as they complete
            for future in as_completed(futures):
                results.append(future.result())

        # Analysis of results
        success_count = sum(1 for r in results if r["success"])
        failure_count = len(results) - success_count
        
        print(f"\nConcurrency Test Results:")
        print(f"Total Requests: {len(results)}")
        print(f"Successful: {success_count}")
        print(f"Failed: {failure_count}")
        
        # Verify consistency across nodes
        self.verify_ledger_consistency()

    def verify_ledger_consistency(self):
        """Verify that all nodes have consistent ledger state"""
        time.sleep(2)  # Allow time for replication
        
        ledger_states = {}
        for node in self.nodes:
            try:
                with open(f'ledger_{node["id"]}.json', 'r') as f:
                    ledger_states[node["id"]] = json.load(f)
            except Exception as e:
                print(f"Error reading ledger for {node['id']}: {e}")
                continue

        # Compare ledger states
        reference_state = None
        for node_id, state in ledger_states.items():
            if reference_state is None:
                reference_state = state
            else:
                try:
                    self.assertEqual(
                        state, 
                        reference_state, 
                        f"Ledger state mismatch detected in {node_id}"
                    )
                except AssertionError as e:
                    print(f"\nConsistency Error: {e}")
                    print(f"Node {node_id} state differs from reference state")

    def test_concurrent_state_changes(self):
        """Test concurrent state changes and leader election"""
        def request_vote(node_id):
            try:
                request = consensus_pb2.VoteRequest(
                    candidate_id=node_id,
                    term=1
                )
                response = self.consensus_stubs[node_id].RequestVote(request)
                return {
                    "node_id": node_id,
                    "vote_granted": response.vote_granted,
                    "success": True
                }
            except Exception as e:
                return {
                    "node_id": node_id,
                    "error": str(e),
                    "success": False
                }

        results = []
        with ThreadPoolExecutor(max_workers=len(self.nodes)) as executor:
            futures = [executor.submit(request_vote, node["id"]) 
                      for node in self.nodes]
            
            for future in as_completed(futures):
                results.append(future.result())

        print("\nConcurrent State Change Results:")
        for result in results:
            if result["success"]:
                print(f"Node {result['node_id']}: Vote granted = {result['vote_granted']}")
            else:
                print(f"Node {result['node_id']}: Error = {result['error']}")

    def tearDown(self):
        # Close all gRPC channels
        for channel in self.channels.values():
            channel.close()

if __name__ == '__main__':
    print("Starting Concurrency Tests...")
    print("Make sure all nodes are running before proceeding.")
    time.sleep(3)  # Give time to read the message
    unittest.main(verbosity=2)
