import time

class Cache:
    def __init__(self):
        self.cache = {}
        self.expiry_times = {}

    def set(self, key, value, ttl=300):
        self.cache[key] = value
        self.expiry_times[key] = time.time() + ttl

    def get(self, key):
        if key in self.cache and time.time() < self.expiry_times[key]:
            return self.cache[key]
        elif key in self.cache:
            del self.cache[key]
            del self.expiry_times[key]
        return None
