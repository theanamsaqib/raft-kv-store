# This is my entire database. Just a Python dictionary with some print statements.

class StateMachine:
    def __init__(self):
        self.data = {}

    def set(self, key, value):
        self.data[key] = value
        print(f"[KV] SET {key} = {value}")

    def get(self, key):
        value = self.data.get(key, None)
        print(f"[KV] GET {key} = {value}")
        return value

    def delete(self, key):
        if key in self.data:
            del self.data[key]
            print(f"[KV] DELETE {key}")

    def show_all(self):
        print(f"[KV] Current data: {self.data}")