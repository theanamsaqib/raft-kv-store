import socket
import json

def send_message(port, message):
    try:
        client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client.settimeout(2)
        client.connect(("localhost", port))
        client.send(json.dumps(message).encode())
        reply = client.recv(4096)
        client.close()
        return json.loads(reply.decode())
    except Exception as e:
        print(f"Error talking to port {port}: {e}")
        return None

print("Forcing split brain...")
r1 = send_message(5002, {"type": "force_leader"})
r2 = send_message(5003, {"type": "force_leader"})
print(f"Node B response: {r1}")
print(f"Node C response: {r2}")
print("\nDone! Both nodes now think they are leader.")
print("Watch the oracle terminal — it should detect and fix this in 3 seconds!")