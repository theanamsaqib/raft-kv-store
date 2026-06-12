import socket
import json
import threading
import time
import random
from state_machine import StateMachine
from log import Log

PEERS = [5001, 5002, 5003, 5004]
MY_PORT = 5005
MY_NAME = "node_e"

state = "follower"
current_term = 0
last_heartbeat = time.time() + random.uniform(0, 3)

db = StateMachine()
log = Log("node_e.log")
lock = threading.Lock()

def send_message(port, message):
    try:
        client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client.settimeout(0.5)
        client.connect(("localhost", port))
        client.send(json.dumps(message).encode())
        reply = client.recv(4096)
        client.close()
        return json.loads(reply.decode())
    except:
        return None

def replicate_to_followers(command):
    confirmations = [1]
    conf_lock = threading.Lock()
    threads = []

    def send_to_peer(port):
        r = send_message(port, {
            "type": "append_entries",
            "from": MY_NAME,
            "term": current_term,
            "command": command
        })
        if r and r.get("success"):
            with conf_lock:
                confirmations[0] += 1

    for port in PEERS:
        t = threading.Thread(target=send_to_peer, args=(port,))
        threads.append(t)
        t.start()
    for t in threads:
        t.join()

    majority = (len(PEERS) + 1) // 2 + 1
    return confirmations[0] >= majority

def handle_client_command(command):
    if state != "leader":
        return {"success": False, "error": "I am not the leader"}
    majority_confirmed = replicate_to_followers(command)
    if majority_confirmed:
        with lock:
            log.append(current_term, command)
            if command["op"] == "SET":
                db.set(command["key"], command["value"])
            elif command["op"] == "DELETE":
                db.delete(command["key"])
        return {"success": True}
    else:
        return {"success": False, "error": "Could not reach majority"}

def handle_get(key):
    value = db.get(key)
    return {"success": True, "value": value}

def send_heartbeats():
    while True:
        time.sleep(0.3)
        if state == "leader":
            threads = []
            for port in PEERS:
                t = threading.Thread(target=send_message, args=(port, {
                    "type": "heartbeat", "from": MY_NAME, "term": current_term
                }))
                threads.append(t)
                t.start()
            for t in threads:
                t.join()

def request_votes_parallel():
    votes = [1]
    vote_lock = threading.Lock()
    threads = []

    def ask_peer(port):
        r = send_message(port, {
            "type": "vote_request",
            "from": MY_NAME,
            "term": current_term
        })
        if r and r.get("vote") == "yes":
            with vote_lock:
                votes[0] += 1

    for port in PEERS:
        t = threading.Thread(target=ask_peer, args=(port,))
        threads.append(t)
        t.start()
    for t in threads:
        t.join()
    return votes[0]

def start_election():
    global state, current_term, last_heartbeat
    state = "candidate"
    current_term += 1
    print(f"\n[{MY_NAME}] Starting election for term {current_term}")

    votes = request_votes_parallel()
    majority = (len(PEERS) + 1) // 2 + 1

    if votes >= majority:
        state = "leader"
        last_heartbeat = time.time()
        print(f"[{MY_NAME}] Won with {votes} votes! Now leader for term {current_term}\n")
        threads = []
        for port in PEERS:
            t = threading.Thread(target=send_message, args=(port, {
                "type": "heartbeat", "from": MY_NAME, "term": current_term
            }))
            threads.append(t)
            t.start()
        for t in threads:
            t.join()
    else:
        state = "follower"
        last_heartbeat = time.time()
        print(f"[{MY_NAME}] Lost election ({votes} votes). Back to follower.")

def watch_timeout():
    while True:
        timeout = random.uniform(0.8, 1.5)
        start = time.time()
        while True:
            time.sleep(0.05)
            if state != "follower":
                break
            if time.time() - last_heartbeat > timeout:
                start_election()
                break

def handle_connection(conn):
    global last_heartbeat, state, current_term
    try:
        data = conn.recv(4096)
        msg = json.loads(data.decode())

        if msg["type"] == "heartbeat":
            if msg["term"] >= current_term:
                last_heartbeat = time.time()
                if state != "follower":
                    state = "follower"
                conn.send(json.dumps({"type": "ack"}).encode())
            else:
                conn.send(json.dumps({"type": "ack"}).encode())

        elif msg["type"] == "vote_request":
            if msg["term"] > current_term and state != "leader":
                current_term = msg["term"]
                last_heartbeat = time.time()
                conn.send(json.dumps({"vote": "yes"}).encode())
            elif msg["term"] == current_term and state == "follower":
                conn.send(json.dumps({"vote": "yes"}).encode())
            else:
                conn.send(json.dumps({"vote": "no"}).encode())

        elif msg["type"] == "append_entries":
            command = msg["command"]
            with lock:
                log.append(msg["term"], command)
                if command["op"] == "SET":
                    db.set(command["key"], command["value"])
                elif command["op"] == "DELETE":
                    db.delete(command["key"])
            conn.send(json.dumps({"success": True}).encode())

        elif msg["type"] == "set":
            result = handle_client_command({"op": "SET", "key": msg["key"], "value": msg["value"]})
            conn.send(json.dumps(result).encode())

        elif msg["type"] == "get":
            result = handle_get(msg["key"])
            conn.send(json.dumps(result).encode())

        elif msg["type"] == "delete":
            result = handle_client_command({"op": "DELETE", "key": msg["key"]})
            conn.send(json.dumps(result).encode())

        elif msg["type"] == "status":
            conn.send(json.dumps({
                "success": True,
                "state": state,
                "term": current_term,
                "log_length": len(log.entries)
            }).encode())

        elif msg["type"] == "demote":
            print(f"[{MY_NAME}] Oracle demoted me! Stepping down to follower.")
            state = "follower"
            last_heartbeat = time.time()
            conn.send(json.dumps({"success": True}).encode())

        elif msg["type"] == "sync":
            sync_port = msg["sync_from_port"]
            entries = send_message(sync_port, {"type": "get_log"})
            if entries:
                with lock:
                    log.entries = entries["entries"]
                    log.save()
                    db.data = {}
                    for entry in log.entries:
                        cmd = entry["command"]
                        if cmd["op"] == "SET":
                            db.set(cmd["key"], cmd["value"])
                        elif cmd["op"] == "DELETE":
                            db.delete(cmd["key"])
                print(f"[{MY_NAME}] Sync complete. {len(log.entries)} entries replayed.")
            conn.send(json.dumps({"success": True}).encode())

        elif msg["type"] == "get_log":
            conn.send(json.dumps({"success": True, "entries": log.entries}).encode())

        elif msg["type"] == "force_leader":
            state = "leader"
            conn.send(json.dumps({"success": True}).encode())

    except Exception as e:
        print(f"[{MY_NAME}] Connection error: {e}")
    finally:
        conn.close()

def start_server():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind(("localhost", MY_PORT))
    server.listen(20)
    while True:
        conn, addr = server.accept()
        threading.Thread(target=handle_connection, args=(conn,), daemon=True).start()

threading.Thread(target=start_server, daemon=True).start()
threading.Thread(target=watch_timeout, daemon=True).start()
threading.Thread(target=send_heartbeats, daemon=True).start()

print(f"[{MY_NAME}] Started on port {MY_PORT}. Waiting for election...\n")
while True:
    time.sleep(1)
