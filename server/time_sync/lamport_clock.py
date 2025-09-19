# /server/time_sync/lamport_clock.py

class LamportClock:
    def __init__(self):
        self.counter = 0

    def tick(self):
        """Increment local counter on local event"""
        self.counter += 1
        return self.counter

    def update(self, received_counter: int):
        """
        Update the counter based on received message
        """
        self.counter = max(self.counter, received_counter) + 1
        return self.counter

    def get_time(self):
        """Return current Lamport time"""
        return self.counter


# Example usage
if __name__ == "__main__":
    clock = LamportClock()
    print("Initial time:", clock.get_time())
    clock.tick()
    print("After local event:", clock.get_time())
    clock.update(5)
    print("After receiving remote event (5):", clock.get_time())
