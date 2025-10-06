import grpc
import sys
from common import utils
from proto import payment_pb2
from proto import payment_pb2_grpc
import uuid
from proto import consensus_pb2, consensus_pb2_grpc
from datetime import datetime

class PaymentResponse:
    """
    Simple response object to mimic your test usage
    """
    def __init__(self, status="SUCCESS", tx_id=None):
        self.status = status
        self.tx_id = tx_id or str(uuid.uuid4())
class PaymentClient:
    """
    Client to send payment requests to a Raft node
    """
    def __init__(self, client_id, node_address):
        self.client_id = client_id
        self.node_address = node_address  # example: "localhost:50051"
    
    def process_payment(self, amount):
        """
        Send a payment request to the node.
        Returns PaymentResponse.
        """
        try:
            with grpc.insecure_channel(self.node_address) as channel:
                stub = consensus_pb2_grpc.ConsensusServiceStub(channel)

                # Prepare a log entry
                timestamp = datetime.now().isoformat()
                tx_id = f"{self.client_id}-{uuid.uuid4()}"
                
                entry = consensus_pb2.LogEntry(
                    user_id=self.client_id,
                    amount=amount,
                    status="PENDING",
                    timestamp=timestamp
                )

                # Wrap in AppendEntriesRequest (simulate leader handling)
                request = consensus_pb2.AppendEntriesRequest(
                    term=0,  # term will be ignored by follower
                    leader_id=self.client_id,  # your leader logic will update
                    prev_log_index=-1,
                    prev_log_term=0,
                    entries=[entry],
                    leader_commit=-1
                )

                response = stub.AppendEntries(request, timeout=5)

                # Return response object
                status = "SUCCESS" if response.success else "FAILED"
                return PaymentResponse(status=status, tx_id=tx_id)

        except grpc.RpcError as e:
            return PaymentResponse(status="FAILED")


def run():
    """
    Client to send payment requests to the distributed payment server.
    """

    # Load server address from env/config
    server_address = utils.get_config("SERVER_ADDRESS", "localhost:50051")

    # Establish channel
    channel = grpc.insecure_channel(server_address)
    stub = payment_pb2_grpc.PaymentServiceStub(channel)

    print("--- Payment Client ---")
    print("Connected to server:", server_address)

    while True:
        try:
            # Ask user for payment input
            user_id = input("Enter User ID (or 'exit' to quit): ")
            if user_id.lower() == "exit":
                break

            amount = float(input("Enter Payment Amount: "))

            # Create request
            request = payment_pb2.PaymentRequest(
                user_id=user_id,
                amount=amount
            )

            # Send request to server
            response = stub.ProcessPayment(request)
            print(f"[SERVER RESPONSE] Status: {response.status}, Message: {response.message}")

        except grpc.RpcError as e:
            print(f"[ERROR] gRPC error: {e.code()} - {e.details()}")
        except Exception as e:
            print(f"[ERROR] {e}")


if __name__ == "__main__":
    run()
