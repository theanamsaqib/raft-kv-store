import socket
import json
import time
import threading

NODES = [
    {"name": "node_a", "port": 5001},
    {"name": "node_b", "port": 5002},
    {"name": "node_c", "port": 5003},
    {"name": "node_d", "port": 5004},
    {"name": "node_e", "port": 5005},
]

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

def get_node_status(node):
    r = send_message(node["port"], {"type": "status"})
    if r:
        return {
            "name": node["name"],
            "port": node["port"],
            "alive": True,
            "state": r.get("state"),
            "term": r.get("term"),
            "log_length": r.get("log_length")
        }
    return {
        "name": node["name"],
        "port": node["port"],
        "alive": False,
        "state": None,
        "term": 0,
        "log_length": 0
    }

def demote_node(node):
    print(f"[Oracle] Demoting {node['name']} on port {node['port']}")
    send_message(node["port"], {"type": "demote"})

def sync_node(loser, winner):
    print(f"[Oracle] Telling {loser['name']} to sync from {winner['name']}")
    send_message(loser["port"], {
        "type": "sync",
        "sync_from_port": winner["port"]
    })

def check_for_split_brain():
    while True:
        time.sleep(3)

        statuses = [get_node_status(n) for n in NODES]
        alive = [s for s in statuses if s["alive"]]
        leaders = [s for s in alive if s["state"] == "leader"]

        print(f"\n[Oracle] Checking cluster...")
        for s in statuses:
            if s["alive"]:
                print(f"  {s['name']} — state: {s['state']}, term: {s['term']}, log: {s['log_length']} entries")
            else:
                print(f"  {s['name']} — DEAD")

        if len(leaders) == 0:
            print(f"[Oracle] No leader found — cluster may be down")

        elif len(leaders) == 1:
            print(f"[Oracle] Healthy — leader is {leaders[0]['name']}")

        elif len(leaders) > 1:
            print(f"\n[Oracle] SPLIT BRAIN DETECTED! {len(leaders)} leaders found!")
            print(f"[Oracle] Leaders: {[l['name'] for l in leaders]}")

            # find the winner — whoever has more log entries
            winner = max(leaders, key=lambda x: x["log_length"])
            losers = [l for l in leaders if l["name"] != winner["name"]]

            print(f"[Oracle] Winner: {winner['name']} ({winner['log_length']} log entries)")

            for loser in losers:
                print(f"[Oracle] Loser: {loser['name']} ({loser['log_length']} log entries)")
                # Step 1 — demote the loser
                demote_node(loser)
                # Step 2 — tell it to sync from winner
                sync_node(loser, winner)

            print(f"[Oracle] Split brain resolved!")

threading.Thread(target=check_for_split_brain, daemon=True).start()

print("[Oracle] Started. Watching cluster for split brain...\n")
while True:
    time.sleep(1)