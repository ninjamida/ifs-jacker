from ij_comm_base import IJCI_Base
from ij_command_conversion import command_dict_to_str, command_str_to_dict
import time

class IJP_Base:
    def __init__(self, connection: IJCI_Base):
        self.connection = connection

    def receive_command(self, wait_timeout: float = 0) -> dict[str, str] | None:
        result = None
        deadline = time.ticks_add(time.ticks_ms(), int(wait_timeout * 1000))
        while time.ticks_diff(deadline, time.ticks_ms()) > 0:
            if self.connection.check_receive():
                new_cmd = self.translate_command(self.connection.receive())
                if new_cmd:
                    result = new_cmd
                break
        return result

    def check_receive_commands(self) -> bool:
        return self.connection.check_receive()
        
    def send_response(self, response: dict[str, str]):
        new_response = self.translate_response(response)
        if new_response:
            self.connection.send(new_response)

    def translate_command(self, message: bytes) -> dict[str, str] | None:
        return None
    
    def translate_response(self, response: dict[str, str]) -> bytes | None:
        return None

class IJP_Text_Based(IJP_Base):
    def __init__(self, connection: IJCI_Base, seperator: str | None = None):
        super().__init__(connection)
        self.seperator = seperator

    def translate_command(self, message: bytes) -> dict[str, str] | None:
        text_cmd = str(message, 'utf-8')

        if self.seperator == None:
            elements = text_cmd.split()
        else:
            elements = text_cmd.split(self.seperator)
        
        if len(elements) == 0:
            return None

        translate_function = getattr(self, f'translate_in_{elements[0]}', None)
        if translate_function == None:
            return None
        else:
            return translate_function(elements)
    
    def translate_response(self, response: dict[str, str]) -> bytes | None:
        command = response.get('command', None)
        if command == None:
            return None
        translate_function = getattr(self, f'translate_out_{command}', None)
        if translate_function == None:
            return None
        else:
            result = translate_function(response)
            if result:
                return result.encode('utf-8')
            else:
                return None
        
class IJP_Text_Based_Direct(IJP_Base):
    # Directly takes IFS Jacker internal commands, and relays IFS Jacker internal responses.
    # This is intended for use with custom printers / custom integrations into other printers,
    # as it is likely cleaner than trying to emulate an AD5X.
    def translate_command(self, message: bytes) -> dict[str, str] | None:
        return command_str_to_dict(str(message, 'utf-8'))
    
    def translate_response(self, response: dict[str, str]) -> bytes | None:
        result = command_dict_to_str(response)
        if result == None:
            return None
        else:
            return result.encode('utf-8')