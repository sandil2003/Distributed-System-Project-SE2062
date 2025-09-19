import grpc
import time
from concurrent import futures

import config
from common import utils

# Import generated stubs
import payment_pb2_grpc
import consensus_pb2_grpc
import replication_pb2_grpc

# Import your service implementations
from server.consensus.raft import ConsensusService
from server.replication.sync_manager import ReplicationService
from server.node.node_server import PaymentService


def serve():
    """
    Starts the gRPC server and registers all services.
    """
    utils.log_event(f"Starting gRPC server for {config.NODE_ID} "
                    f"on {config.SERVER_HOST}:{config.SERVER_PORT}")

    # Thread pool for handling multiple RPC calls
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))

    # Register all services
    payment_pb2_grpc.add_PaymentServiceServicer_to_server(PaymentService(), server)
    consensus_pb2_grpc.add_ConsensusServiceServicer_to_server(ConsensusService(), server)
    replication_pb2_grpc.add_ReplicationServiceServicer_to_server(ReplicationService(), server)

    # Bind to host and port
    server.add_insecure_port(f"{config.SERVER_HOST}:{config.SERVER_PORT}")
    server.start()

    utils.log_event("gRPC server started successfully and waiting for requests.")

    try:
        while True:
            time.sleep(10)  # keep process alive
    except KeyboardInterrupt:
        utils.log_event("Shutting down gRPC server...")
        server.stop(0)


if __name__ == "__main__":
    serve()
