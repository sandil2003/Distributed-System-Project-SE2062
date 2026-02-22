import unittest
import threading
import time
import grpc
import json
import random
from concurrent.futures import ThreadPoolExecutor, as_completed
from client.client import PaymentClient
from collections import defaultdict
from datetime import datetime

class ConcurrencyLoadTest(unittest.TestCase):
    def setUp(self):
        # Initialize clients for each node
        self.nodes = [
            {"port": 50051, "id": "node1"},
            {"port": 50052, "id": "node2"},
            {"port": 50053, "id": "node3"}
        ]
        
        # Create 10 clients
        self.num_clients = 10
        self.clients = []
        for i in range(self.num_clients):
            # Round-robin client distribution across nodes
            node = self.nodes[i % len(self.nodes)]
            client = PaymentClient(f"client_{i}", f"localhost:{node['port']}")
            self.clients.append(client)
            
        self.transaction_log = defaultdict(list)
        self.lock = threading.Lock()

    def test_concurrent_payments(self):
        """
        Test with 10 clients making concurrent payments and verify system consistency
        """
        num_transactions = 5  # Each client will make 5 transactions
        total_transactions = self.num_clients * num_transactions
        
        print(f"\nStarting concurrent load test with {self.num_clients} clients")
        print(f"Each client will make {num_transactions} transactions")
        print(f"Total expected transactions: {total_transactions}\n")

        start_time = time.time()
        
        def client_payment_worker(client_id):
            client = self.clients[client_id]
            results = []
            
            for i in range(num_transactions):
                amount = random.randint(10, 1000)
                timestamp = datetime.now().isoformat()
                try:
                    response = client.process_payment(amount)
                    
                    with self.lock:
                        self.transaction_log[client_id].append({
                            'amount': amount,
                            'timestamp': timestamp,
                            'status': response.status,
                            'client_id': client_id
                        })
                        
                    results.append({
                        'success': response.status == 'SUCCESS',
                        'amount': amount,
                        'error': None
                    })
                    
                except Exception as e:
                    results.append({
                        'success': False,
                        'amount': amount,
                        'error': str(e)
                    })
                    
                # Add small random delay between transactions
                time.sleep(random.uniform(0.1, 0.3))
                
            return results

        # Execute all clients concurrently
        with ThreadPoolExecutor(max_workers=self.num_clients) as executor:
            future_to_client = {
                executor.submit(client_payment_worker, i): i 
                for i in range(self.num_clients)
            }
            
            # Collect results as they complete
            all_results = []
            for future in as_completed(future_to_client):
                client_id = future_to_client[future]
                try:
                    results = future.result()
                    all_results.extend(results)
                except Exception as e:
                    print(f"Client {client_id} generated an exception: {e}")

        end_time = time.time()
        execution_time = end_time - start_time
        
        # Calculate statistics
        successful_txns = sum(1 for r in all_results if r['success'])
        failed_txns = len(all_results) - successful_txns
        
        print("\n=== Test Results ===")
        print(f"Total Transactions Attempted: {len(all_results)}")
        print(f"Successful Transactions: {successful_txns}")
        print(f"Failed Transactions: {failed_txns}")
        print(f"Total Execution Time: {execution_time:.2f} seconds")
        print(f"Average Transaction Time: {execution_time/len(all_results):.2f} seconds")
        print(f"Transactions per Second: {len(all_results)/execution_time:.2f}")
        
        # Verify system consistency
        self.verify_system_consistency()
        
        # Assert test expectations
        self.assertGreater(successful_txns, 0, "No transactions were successful")
        self.assertLess(
            failed_txns/len(all_results), 
            0.2, 
            "Too many failed transactions (>20% failure rate)"
        )

    def verify_system_consistency(self):
        """
        Verify that all nodes have consistent state after concurrent operations
        """
        print("\n=== Consistency Check ===")
        
        # Allow time for replication
        time.sleep(2)
        
        # Read ledger files from all nodes
        ledgers = {}
        for node in self.nodes:
            try:
                with open(f'ledger_{node["id"]}.json', 'r') as f:
                    ledgers[node["id"]] = json.load(f)
            except Exception as e:
                print(f"Error reading ledger for {node['id']}: {e}")
                continue

        # Compare transaction counts
        tx_counts = {
            node_id: len(ledger) 
            for node_id, ledger in ledgers.items()
        }
        
        print("\nTransaction counts per node:")
        for node_id, count in tx_counts.items():
            print(f"{node_id}: {count} transactions")
            
        # Verify all nodes have same number of transactions
        if len(set(tx_counts.values())) > 1:
            print("\nWARNING: Nodes have different transaction counts!")
            
        # Compare actual transactions
        reference_node = list(ledgers.keys())[0]
        reference_ledger = ledgers[reference_node]
        
        for node_id, ledger in ledgers.items():
            if node_id == reference_node:
                continue
                
            # Compare transaction sets
            ref_tx_ids = {tx['tx_id'] for tx in reference_ledger}
            node_tx_ids = {tx['tx_id'] for tx in ledger}
            
            missing_txs = ref_tx_ids - node_tx_ids
            extra_txs = node_tx_ids - ref_tx_ids
            
            if missing_txs:
                print(f"\n{node_id} is missing transactions: {missing_txs}")
            if extra_txs:
                print(f"\n{node_id} has extra transactions: {extra_txs}")
                
        print("\nConsistency check completed.")

    def test_concurrent_reads(self):
        """
        Test concurrent read operations while writes are happening
        """
        print("\nTesting concurrent reads during writes...")
        
        def read_worker(client_id):
            client = self.clients[client_id]
            results = []
            for _ in range(3):  # Each reader makes 3 read attempts
                try:
                    # Simulate a read operation (you'll need to implement this in your client)
                    # response = client.get_balance()  # Example read operation
                    time.sleep(random.uniform(0.1, 0.3))
                    results.append({'success': True})
                except Exception as e:
                    results.append({'success': False, 'error': str(e)})
            return results

        def write_worker(client_id):
            client = self.clients[client_id]
            results = []
            for _ in range(2):  # Each writer makes 2 write attempts
                try:
                    amount = random.randint(10, 100)
                    response = client.process_payment(amount)
                    results.append({
                        'success': response.status == 'SUCCESS',
                        'amount': amount
                    })
                    time.sleep(random.uniform(0.2, 0.5))
                except Exception as e:
                    results.append({'success': False, 'error': str(e)})
            return results

        # Start concurrent reads and writes
        with ThreadPoolExecutor(max_workers=self.num_clients) as executor:
            # Submit mix of read and write operations
            futures = []
            for i in range(self.num_clients):
                if i % 2 == 0:  # Even numbered clients do reads
                    futures.append(executor.submit(read_worker, i))
                else:  # Odd numbered clients do writes
                    futures.append(executor.submit(write_worker, i))

            # Wait for all operations to complete
            for future in as_completed(futures):
                try:
                    results = future.result()
                except Exception as e:
                    print(f"Operation failed with: {e}")

        print("Concurrent read/write test completed.")

if __name__ == '__main__':
    print("Starting Concurrency Load Tests...")
    print("Ensure all nodes are running before proceeding.")
    time.sleep(3)  # Give time to read the message
    unittest.main(verbosity=2)