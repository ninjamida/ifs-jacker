from ij_comm_base import IJCI_Base
from ij_console import console
import os

debug_comm_interfaces: dict[str, IJCI_Debug] = {}

def get_debug_comm_interfaces() -> dict[str, IJCI_Debug]:
    return debug_comm_interfaces

class IJCI_Debug(IJCI_Base):
    def __init__(self, id: str | None, responder = None):
        global debug_comm_interfaces
        self.receive_queue: list[str] = []
        if id in debug_comm_interfaces or id is None:
            i = 0
            while f'debug{i}' in debug_comm_interfaces:
                i += 1
            id = f'debug{i}'
        self.identifier = id
        debug_comm_interfaces[id] = self
        self.friendly_name = f'Debug Comm {id}'
        self.responder = responder

    def send(self, message: bytes):
        try:
            message_str = str(message, 'utf-8')
        except:
            message_str = message.hex(' ')
        console().write(f'{self.identifier} << {message_str}', 'comm')
        if self.responder:
            self.responder.respond(message_str, self.receive_queue)

    def check_receive(self) -> bool:
        return len(self.receive_queue) > 0
    
    def receive(self) -> bytes:
        if len(self.receive_queue) == 0:
            return bytes()
        else:
            return self.receive_queue.pop(0).encode('utf-8')
        
    @staticmethod
    def make_from_config(config_data: dict[str, str]) -> IJCI_Debug:
        responder = None
        responder_type = config_data.get('responder', None)
        if responder_type:
            module_classes = {}

            for file in os.listdir('.'):
                if file.startswith('ij_debug_responder_') and file.endswith('.py'):
                    module_name = file[:-3]
                    module = __import__(module_name)
                    for name, attr in module.__dict__.items():
                        if name.startswith('IJDR_'):
                            if isinstance(attr, type):
                                module_classes[name] = attr

            responder_class = module_classes.get(f'IJDR_{responder_type}')
            if responder_class:
                responder = responder_class()

        return IJCI_Debug(config_data.get('id', None), responder)

    