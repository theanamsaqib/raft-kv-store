import socket
import json
from fastapi import FastAPI
from fastapi.responses import JSONResponse

app = FastAPI()

NODES = [5001, 5002, 5003, 5004, 5005]

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

def find_leader_and_send(message):
    for port in NODES:
        r = send_message(port, message)
        if r and r.get("success"):
            return r
    return {"success": False, "error": "No leader found"}

@app.get("/set")
def set_value(key: str, value: str):
    result = find_leader_and_send({
        "type": "set",
        "key": key,
        "value": value
    })
    return JSONResponse(result)

@app.get("/get")
def get_value(key: str):
    for port in NODES:
        r = send_message(port, {"type": "get", "key": key})
        if r and r.get("value") is not None:
            return JSONResponse(r)
    return JSONResponse({"success": False, "error": "Key not found"})

@app.get("/delete")
def delete_value(key: str):
    result = find_leader_and_send({
        "type": "delete",
        "key": key
    })
    return JSONResponse(result)

@app.get("/status")
def status():
    nodes = []
    for port in NODES:
        r = send_message(port, {"type": "get", "key": "ping"})
        nodes.append({
            "port": port,
            "alive": r is not None
        })
    return JSONResponse({"nodes": nodes})