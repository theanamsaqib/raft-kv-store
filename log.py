import json
import os
import time

class Log:
    def __init__(self, filename):
        self.filename = filename
        self.entries = []
        self.load()

    def append(self, term, command):
        entry = {"term": term, "command": command}
        self.entries.append(entry)
        self.save()
        print(f"[LOG] Appended: {entry}")

    def save(self):
        start = time.time()
        with open(self.filename, "w") as f:
            json.dump(self.entries, f)
        elapsed = time.time() - start
        if elapsed > 0.1:
            print(f"[LOG] WARNING: save took {elapsed:.3f}s")

    def load(self):
        if os.path.exists(self.filename):
            with open(self.filename, "r") as f:
                self.entries = json.load(f)
            print(f"[LOG] Loaded {len(self.entries)} entries from disk")
        else:
            self.entries = []

    def get_all(self):
        return self.entries