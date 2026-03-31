from ij_comm_interfaces import IJCI_Base
import time

class IJM_Base:
    def __init__(self, connection: IJCI_Base):
        self.connection = connection
        self.command_response_wait_timeout = 1
        self.friendly_name = "Base_Placeholder"

    def get_channel_count(self) -> int:
        return 0
    
    def receive_data(self, wait_timeout: float = 0) -> dict[str, str] | None:
        result = None
        deadline = time.ticks_add(time.ticks_ms(), int(wait_timeout * 1000))
        while time.ticks_diff(deadline, time.ticks_ms()) > 0:
            if self.connection.check_receive():
                new_response = self.translate_response(self.connection.receive())
                if new_response:
                    result = new_response
                break
        return result
    
    def check_receive_data(self) -> bool:
        return self.connection.check_receive()
    
    def send_command(self, command: dict[str, str], wait_for_response: bool = True) -> dict[str, str] | None:
        new_cmd = self.translate_command(command)
        if new_cmd:
            self.connection.send(new_cmd)
        if wait_for_response:
            return self.receive_data(self.command_response_wait_timeout)
        else:
            return None

    def translate_command(self, command: dict[str, str]) -> bytes | None:
        return None
    
    def translate_response(self, message: bytes) -> dict[str, str] | None:
        return None
    
class IJM_Text_Based(IJM_Base):
    def __init__(self, connection: IJCI_Base, seperator: str | None = None):
        super().__init__(connection)
        self.seperator = seperator
        self.friendly_name = "Base_Placeholder_Text_Based"
    
    def translate_response(self, message: bytes) -> dict[str, str] | None:
        text_response = str(message, 'utf-8')

        if self.seperator == None:
            elements = text_response.split()
        else:
            elements = text_response.split(self.seperator)
        
        if len(elements) == 0:
            return None

        translate_function = getattr(self, f'translate_in_{elements[0]}', None)
        if translate_function == None:
            return None
        else:
            return translate_function(elements)
    
    def translate_command(self, command: dict[str, str]) -> bytes | None:
        command_action = command.get('command', None)
        if command_action == None:
            return None
        translate_function = getattr(self, f'translate_out_{command_action}', None)
        if translate_function == None:
            return None
        else:
            result = translate_function(command)
            if result:
                return result.encode('utf-8')
            else:
                return None