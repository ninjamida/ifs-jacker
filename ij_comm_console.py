# If this is being used, user-facing console must be disabled in the settings.

import sys
import uselect
from ij_comm_base import IJCI_Base

class IJCI_Console(IJCI_Base):
    def __init__(self):
        super().__init__()
        self.buffer = ''
        self.queue = []
        self.polling = uselect.poll()
        self.polling.register(sys.stdin, uselect.POLLIN)
        self.friendly_name = 'Console'

    def send(self, message: bytes):
        try:
            print(str(message, 'utf-8'))
        except:
            print(message.hex(' '))

    def check_receive(self) -> bool:
        return len(self.queue) > 0
    
    def receive(self) -> bytes:
        if len(self.queue) == 0:
            return bytes()
        else:
            return self.queue.pop(0).encode('utf-8')

    def update(self):
        if self.polling.poll(0):
            char = sys.stdin.read(1)
            if char in ['\r', '\n']:
                self.queue += self.buffer
                self.buffer = ''
            elif ord(char) >= 32 and ord(char) < 127:
                self.buffer += char

    @staticmethod
    def make_from_config(config_data: dict[str, str]) -> IJCI_Console:
        return IJCI_Console()