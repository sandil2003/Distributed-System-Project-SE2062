# /server/time_sync/ntp_sync.py

import ntplib
from time import ctime

class NTPClient:
    def __init__(self, server="pool.ntp.org"):
        self.server = server
        self.client = ntplib.NTPClient()

    def get_time(self):
        """
        Fetch current UTC time from NTP server
        """
        try:
            response = self.client.request(self.server)
            return ctime(response.tx_time)  # human-readable
        except Exception as e:
            print(f"[NTP ERROR] Could not fetch time: {e}")
            return None


# Example usage
if __name__ == "__main__":
    ntp = NTPClient()
    current_time = ntp.get_time()
    print("Current NTP time:", current_time)
