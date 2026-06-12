# Raft Distributed KV Store

A from-scratch implementation of the Raft consensus algorithm in Python, built without any consensus libraries. Runs as 5 independent processes communicating over raw TCP sockets using a custom JSON-RPC protocol.

## What problem does this solve?

A normal database runs on one machine. If that machine crashes, your data is gone and your app is down. This project runs the same database across 5 machines simultaneously. If any of them crash, the others keep running with zero data loss and automatically elect a new leader within seconds.

## Architecture

```
Client (browser / curl)
        |
   REST API (FastAPI)
        |
   Leader Node  ──────────────────────────────┐
        |                                     │
        ├── Replicate ──→ Follower Node B     │
        ├── Replicate ──→ Follower Node C     │  Quorum Oracle
        ├── Replicate ──→ Follower Node D     │  (split-brain watchdog)
        └── Replicate ──→ Follower Node E     │
                                              └─────────────────────┘
```

## How it works

**Leader election** — every node starts as a follower with a random election timeout (500–900ms). If a follower stops receiving heartbeats, it becomes a candidate, requests votes from all peers in parallel, and becomes leader if it wins a majority. Randomised timeouts prevent split votes.

**Log replication** — every write goes to the leader first. The leader writes it to a write-ahead log on disk, replicates it to all followers in parallel, and only commits it once a majority confirms. This guarantees zero data loss even if the leader crashes mid-write.

**Crash recovery** — every node writes to a WAL (write-ahead log) on disk before applying any command. On restart, the node replays the log to rebuild its state. No data is ever lost.

**Quorum oracle** — a separate watchdog process monitors all nodes every 3 seconds. If it detects two nodes both claiming to be leader (split-brain), it compares their commit indexes, demotes the one with less data, and forces it to sync from the winner. This is an original contribution on top of the standard Raft paper.

## Benchmarks

Measured on a 5-node cluster running on a single Windows laptop over localhost:

| Metric | Result |
|---|---|
| Sequential write throughput | 11.8 ops/sec |
| Success rate | 1000 / 1000 (zero failures) |
| Data loss | Zero |
| Leader failover time | ~5 seconds |
| Split-brain detection | Under 3 seconds |

Note: throughput is bottlenecked by full disk persistence and replication to 4 nodes on every write, not network or CPU. Each write hits disk twice (leader WAL + follower WAL) before being confirmed.

## Project structure

```
node_a.py         — Raft node (port 5001)
node_b.py         — Raft node (port 5002)
node_c.py         — Raft node (port 5003)
node_d.py         — Raft node (port 5004)
node_e.py         — Raft node (port 5005)
oracle.py         — Quorum oracle (split-brain watchdog)
api.py            — FastAPI REST interface
log.py            — Write-ahead log (WAL)
state_machine.py  — In-memory KV store (applied committed entries)
benchmark.py      — Throughput and election speed benchmarks
client.py         — CLI client
test_splitbrain.py — Forces split-brain for testing oracle
```

## How to run

Start all nodes in separate terminals:

```bash
python node_a.py
python node_b.py
python node_c.py
python node_d.py
python node_e.py
python oracle.py
uvicorn api:app --port 8000
```

The cluster self-organises — no configuration needed. One node will win the first election automatically within a few seconds.

## API

```
GET /set?key=name&value=Arjun    write a value
GET /get?key=name                read a value
GET /delete?key=name             delete a value
GET /status                      check cluster health
```

## Testing

```bash
# Run write throughput benchmark
python benchmark.py   # choose option 1 or 3

# Test election speed (kills the leader and measures failover)
python benchmark.py   # choose option 2

# Force a split-brain and watch the oracle fix it
python test_splitbrain.py
```

## What I learned building this

The hardest parts in order:

1. **Log replication edge cases** — the prevLogIndex/prevLogTerm consistency check in AppendEntries is where most Raft implementations break. Getting this right took longer than everything else combined.

2. **Split-brain reconciliation** — designing the oracle protocol required thinking carefully about what "correct" means when two leaders have diverged. The answer is: whoever committed more entries wins, the loser rolls back and replays from the winner.

3. **Concurrent writes under lock contention** — holding a lock across network calls (replication) blocked heartbeats and caused false leader failures. The fix was to replicate first without the lock, then lock only for the disk write.

4. **Port conflicts as silent bugs** — early versions had nodes sharing ports. Messages were delivered to the wrong process with no error. Nothing complained. This caused phantom bugs for hours.

## Tech stack

Python 3.11, raw TCP sockets, threading, JSON, FastAPI, uvicorn

## References

- Raft paper (extended version): https://raft.github.io/raft.pdf
- Designing Data-Intensive Applications — Kleppmann, chapters 5, 8, 9
- MIT 6.824 distributed systems lab 2
