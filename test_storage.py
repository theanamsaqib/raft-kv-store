from state_machine import StateMachine
from log import Log

# Create the log and state machine
log = Log("node_test.log")
db = StateMachine()

# Simulate 3 commands coming in from the leader
commands = [
    {"op": "SET", "key": "name", "value": "Arjun"},
    {"op": "SET", "key": "age", "value": "21"},
    {"op": "SET", "key": "college", "value": "NIT"},
]

for cmd in commands:
    # Step 1 — write to log first (so we survive crashes)
    log.append(term=1, command=cmd)

    # Step 2 — apply to state machine
    if cmd["op"] == "SET":
        db.set(cmd["key"], cmd["value"])
    elif cmd["op"] == "GET":
        db.get(cmd["key"])
    elif cmd["op"] == "DELETE":
        db.delete(cmd["key"])

print("\n--- Final state ---")
db.show_all()

print("\n--- What's saved on disk ---")
for entry in log.get_all():
    print(entry)