# If this is being used, user-facing console must be enabled AND read-only. Only one IJCI_Console comm can be used.
# This is intended for custom implementations where a printer connects in a manner that accesses a console. For
# human debugging use, use IJCI_Debug instead.

import sys
import uselect
from ij_comm_base import IJCI_Base
from ij_console import console

class IJCI_Console(IJCI_Base):
    def __init__(self):
        super().__init__()
        self.buffer = ''
        self.queue = []
        self.polling = uselect.poll()
        self.polling.register(sys.stdin, uselect.POLLIN)
        self.friendly_name = 'Console'

    def update(self):
        if len(self.send_buffer) > 0:
            new_lines = []
            self.send_lock.acquire()
            try:
                while len(self.send_buffer) > 0:
                    new_lines.append(self.send_buffer.pop(0))
            finally:
                self.send_lock.release()
            for line in new_lines:
                console().write(line, 'ConsoleComm')

        if self.polling.poll(0):
            char = sys.stdin.read(1)
            if char in ['\r', '\n']:
                self.receive_lock.acquire()
                try:
                    self.receive_buffer.append(self.buffer.encode('utf-8'))
                finally:
                    self.receive_lock.release()
                self.buffer = ''
            elif ord(char) >= 32 and ord(char) < 127:
                self.buffer += char

    @staticmethod
    def make_from_config(config_data: dict[str, str]) -> IJCI_Console:
        return IJCI_Console()