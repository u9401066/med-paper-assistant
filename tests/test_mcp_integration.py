import json
import os
import subprocess
import sys


def run_mcp_test():
    # Path to the server script
    server_script = os.path.join("src", "med_paper_assistant", "mcp_server", "server.py")

    # Command to run the server
    cmd = [sys.executable, server_script]

    print(f"Starting server: {' '.join(cmd)}")

    # Start the server process
    process = subprocess.Popen(
        cmd,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=sys.stderr,
        text=True,
        bufsize=0,  # Unbuffered
    )

    try:
        # 1. Initialize
        init_request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "test-client", "version": "1.0"},
            },
        }
        print("Sending initialize request...")
        process.stdin.write(json.dumps(init_request) + "\n")
        process.stdin.flush()

        # Read initialize response
        response_line = process.stdout.readline()
        print(f"Received: {response_line.strip()}")
        response = json.loads(response_line)
        if "error" in response:
            print("Initialization failed!")
            return

        # 2. Send initialized notification
        init_notif = {"jsonrpc": "2.0", "method": "notifications/initialized"}
        print("Sending initialized notification...")
        process.stdin.write(json.dumps(init_notif) + "\n")
        process.stdin.flush()

        # 3. List Tools
        list_tools_req = {"jsonrpc": "2.0", "id": 2, "method": "tools/list"}
        print("Sending tools/list request...")
        process.stdin.write(json.dumps(list_tools_req) + "\n")
        process.stdin.flush()

        response_line = process.stdout.readline()
        print(f"Received: {response_line.strip()}")
        response = json.loads(response_line)
        tools = response.get("result", {}).get("tools", [])
        print(f"Found {len(tools)} tools: {[t['name'] for t in tools]}")

        # 4. Call search_literature
        call_req = {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {"name": "search_literature", "arguments": {"query": "asthma", "limit": 1}},
        }
        print("Sending tools/call request (search_literature)...")
        process.stdin.write(json.dumps(call_req) + "\n")
        process.stdin.flush()

        response_line = process.stdout.readline()
        print(f"Received: {response_line.strip()}")
        response = json.loads(response_line)

        if "result" in response:
            content = response["result"].get("content", [])
            for item in content:
                print(f"Tool Output: {item.get('text', '')[:200]}...")
        else:
            print("Tool call failed or returned no result.")

    except Exception as e:
        print(f"Test failed with exception: {e}")
    finally:
        process.terminate()
        process.wait()


if __name__ == "__main__":
    run_mcp_test()
