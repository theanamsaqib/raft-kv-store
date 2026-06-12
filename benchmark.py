import socket
import json
import time
import threading

NODES = [5001, 5002, 5003, 5004, 5005]

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

def find_leader():
    for port in NODES:
        r = send_message(port, {"type": "status"})
        if r and r.get("state") == "leader":
            return port
    return None

def benchmark_writes(n=1000):
    print(f"\nFinding leader...")
    leader = find_leader()
    if not leader:
        print("No leader found! Start your nodes first.")
        return

    print(f"Leader is on port {leader}")
    print(f"Running {n} SET operations...\n")

    start = time.time()
    success = 0
    failed = 0

    for i in range(n):
        r = send_message(leader, {
            "type": "set",
            "key": f"key_{i}",
            "value": f"value_{i}"
        })
        if r and r.get("success"):
            success += 1
        else:
            failed += 1

        if (i + 1) % 100 == 0:
            print(f"  {i + 1}/{n} done...")

    end = time.time()
    duration = end - start
    ops_per_sec = success / duration

    print(f"\n--- SEQUENTIAL WRITE BENCHMARK RESULTS ---")
    print(f"Total operations : {n}")
    print(f"Successful       : {success}")
    print(f"Failed           : {failed}")
    print(f"Total time       : {duration:.2f} seconds")
    print(f"Throughput       : {ops_per_sec:.1f} ops/sec")

def benchmark_writes_concurrent(n=1000, workers=10):
    print(f"\nFinding leader...")
    leader = find_leader()
    if not leader:
        print("No leader found!")
        return

    print(f"Leader is on port {leader}")
    print(f"Running {n} SET operations with {workers} concurrent workers...\n")

    success = [0]
    failed = [0]
    lock = threading.Lock()

    def worker(start, end):
        for i in range(start, end):
            r = send_message(leader, {
                "type": "set",
                "key": f"key_{i}",
                "value": f"value_{i}"
            })
            with lock:
                if r and r.get("success"):
                    success[0] += 1
                else:
                    failed[0] += 1

    start = time.time()

    threads = []
    chunk = n // workers
    for i in range(workers):
        t = threading.Thread(target=worker, args=(i*chunk, (i+1)*chunk))
        threads.append(t)
        t.start()

    for t in threads:
        t.join()

    end = time.time()
    duration = end - start
    ops_per_sec = success[0] / duration

    print(f"\n--- CONCURRENT WRITE BENCHMARK RESULTS ---")
    print(f"Total operations : {n}")
    print(f"Workers          : {workers}")
    print(f"Successful       : {success[0]}")
    print(f"Failed           : {failed[0]}")
    print(f"Total time       : {duration:.2f} seconds")
    print(f"Throughput       : {ops_per_sec:.1f} ops/sec")

def benchmark_election():
    print(f"\n--- ELECTION SPEED BENCHMARK ---")
    print(f"Finding current leader...")

    leader = find_leader()
    if not leader:
        print("No leader found!")
        return

    print(f"Current leader: port {leader}")
    print(f"Kill the leader now with Ctrl+C in its terminal!")
    print(f"Measuring time until new leader elected...\n")

    start = time.time()

    while True:
        r = send_message(leader, {"type": "status"})
        if not r:
            print(f"Leader is down! Waiting for new election...")
            break
        time.sleep(0.1)

    while True:
        new_leader = find_leader()
        if new_leader and new_leader != leader:
            elapsed = time.time() - start
            print(f"New leader elected on port {new_leader}!")
            print(f"Election time: {elapsed:.3f} seconds ({elapsed*1000:.0f}ms)")
            break
        time.sleep(0.05)

print("What do you want to benchmark?")
print("1 — Write throughput sequential (1000 ops)")
print("2 — Election speed (kill leader and measure)")
print("3 — Write throughput concurrent (1000 ops, 10 workers)")
choice = input("\nEnter 1, 2, or 3: ").strip()

if choice == "1":
    benchmark_writes(1000)
elif choice == "2":
    benchmark_election()
elif choice == "3":
    benchmark_writes_concurrent(1000, 10)