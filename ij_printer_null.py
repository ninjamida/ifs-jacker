from ij_comm_interfaces import IJCI_Null
import time

class IJP_Null:
    def __init__(self, connection: IJCI_Null):
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

class IJP_Text_Based(IJP_Null):
    def __init__(self, connection: IJCI_Null, seperator: str | None = None):
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
        
class IJP_Text_Based_Direct(IJP_Null):
    # Directly takes IFS Jacker internal commands, and relays IFS Jacker internal responses.
    # This is intended for use with custom printers / custom integrations into other printers,
    # as it is likely cleaner than trying to emulate an AD5X.
    def translate_command(self, message: bytes) -> dict[str, str] | None:
        params = str(message, 'utf-8').split()
        if len(params) == 0:
            return None
        else:
            result = {'command': params[0]}
            for param in params[1:]:
                param_split = param.split('=', 1)
                if len(param_split) == 2:
                    result[param_split[0]] = param_split[1]
                else:
                    result[param_split[0]] = ''

        return result
    
    def translate_response(self, response: dict[str, str]) -> bytes | None:
        result = response.get('command', None)
        if result == None:
            return None
        
        for key, value in response.items():
            if key == 'command':
                continue
            result += f' {key}={value}'

        return result.encode('utf-8')