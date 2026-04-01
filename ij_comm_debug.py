from ij_comm_base import IJCI_Base
from ij_console import console

debug_comm_interfaces: dict[str, IJCI_Debug] = {}

def get_debug_comm_interfaces() -> dict[str, IJCI_Debug]:
    return debug_comm_interfaces

class IJCI_Debug(IJCI_Base):
    def __init__(self, id: str | None):
        global debug_comm_interfaces
        self.receive_queue: list[str] = []
        if id in debug_comm_interfaces or id is None:
            i = 0
            while f'debug{i}' in debug_comm_interfaces:
                i += 1
            id = f'debug{i}'
        self.identifier = id
        debug_comm_interfaces[id] = self
        self.friendly_name = f'Debug_Comm_{id}'

    def send(self, message: bytes):
        try:
            message_str = str(message, 'utf-8')
        except:
            message_str = message.hex(' ')
        console().lock()
        try:
            console().incoming.append(f'{self.identifier} << {message_str}')
        finally:
            console().release()

    def check_receive(self) -> bool:
        return len(self.receive_queue) > 0
    
    def receive(self) -> bytes:
        if len(self.receive_queue) == 0:
            return bytes()
        else:
            return self.receive_queue.pop(0).encode('utf-8')
        
    @staticmethod
    def make_from_config(config_data: dict[str, str]) -> IJCI_Debug:
        return IJCI_Debug(config_data.get('id', None))

    