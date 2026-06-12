import socket
import json

NODES = [5002, 5003]

def send_message(port, message):
    try:
        client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client.settimeout(2)
        client.connect(("localhost", port))
        client.send(json.dumps(message).encode())
        reply = client.recv(4096)
        client.close()
        return json.loads(reply.decode())
    except:
        return None

def find_leader():
    for port in NODES:
        r = send_message(port, {"type": "get", "key": "ping"})
        if r and r.get("success"):
            return port
    return None

def set_value(key, value):
    for port in NODES:
        r = send_message(port, {"type": "set", "key": key, "value": value})
        if r and r.get("success"):
            print(f"Success! Leader is on port {port}")
            return r
    return {"success": False, "error": "No leader found"}

def get_value(key):
    for port in NODES:
        r = send_message(port, {"type": "get", "key": key})
        if r and r.get("value") is not None:
            return r
    return {"success": False, "error": "Key not found"}

print("Setting name = Arjun...")
r = set_value("name", "Arjun")
print(f"Response: {r}")

print("\nGetting name...")
r = get_value("name")
print(f"Response: {r}")