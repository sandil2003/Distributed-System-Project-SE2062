#
# This script starts a 3-node Raft cluster on the local machine.
# It will open a new terminal window for each node.
#
# To stop the cluster, simply close each of the new terminal windows.
#

# First, kill any existing Python processes and clean up ports
Write-Host "Cleaning up existing processes..."
Get-Process python* | Stop-Process -Force -ErrorAction SilentlyContinue
Get-Process powershell | Where-Object { $_.MainWindowTitle -like "Node: node*" } | Stop-Process -Force
Start-Sleep -Seconds 2

# --- Cluster Configuration ---
$nodes = @(
    @{ nodeId = "node1"; port = 50051 },
    @{ nodeId = "node2"; port = 50052 },
    @{ nodeId = "node3"; port = 50053 }
)

Write-Host "Starting 3-node cluster... (A new window will open for each node)"

# --- Launch Nodes ---
foreach ($node in $nodes) {
    # 1. Construct the PEER_NODES JSON string for the current node.
    # This includes all other nodes in the cluster.
    $peerNodes = @{}
    foreach ($peer in $nodes) {
        if ($peer.nodeId -ne $node.nodeId) {
            $peerNodes[$peer.nodeId] = "localhost:$($peer.port)"
        }
    }
    # Convert the peer nodes hashtable to a compact JSON string.
    $peerNodesJson = $peerNodes | ConvertTo-Json -Compress

    # 2. Define the title for the new terminal window.
    $windowTitle = "Node: $($node.nodeId) | Port: $($node.port)"

    # 3. Start the node in a new PowerShell window with proper argument passing
    $encodedCommand = [Convert]::ToBase64String([System.Text.Encoding]::Unicode.GetBytes(@"
        `$env:NODE_ID = '$($node.nodeId)'
        `$env:SERVER_PORT = '$($node.port)'
        `$env:PEER_NODES = '$($peerNodesJson)'
        `$Host.UI.RawUI.WindowTitle = '$($windowTitle)'
        python -m server.grpc_server
"@))
    
    Start-Process powershell -ArgumentList "-NoExit", "-EncodedCommand", $encodedCommand

    Write-Host "Launched node '$($node.nodeId)' on port $($node.port)."
    # Add a 3-second delay between starting nodes to allow proper initialization
    Start-Sleep -Seconds 3
}

Write-Host "All nodes have been launched."