import subprocess
import datetime

class ConnectedClientsKeepAlive(object):
    """
    Check for number of clients connected to this machine 
    """

    def __init__(self) -> None:
        super().__init__()
        self.last_poll = datetime.datetime.now()

    def poll(self):

        now = datetime.datetime.now()
        if (now - self.last_poll).seconds > 2:

            iw = subprocess.run(["iw", "dev", "wlan0", "station", "dump"], capture_output=True)

            if len(iw.stdout) < 1:
                return False

            self.last_poll = now

        return True