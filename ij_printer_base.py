from ij_comm_base import IJCI_Base, IJCI_Null
from ij_command_conversion import command_dict_to_str, command_str_to_dict
from ij_console import console
import time

class IJP_Base:
    def __init__(self, connection: IJCI_Base):
        self.connection = connection
        self.friendly_name = 'Base_Placeholder'
        self.out_cmd_queue: list[dict[str, str]] = []

    def receive_command(self, wait_timeout: float = 0) -> dict[str, str] | None:
        if len(self.out_cmd_queue) > 0:
            return self.out_cmd_queue.pop(0)
        
        result = None
        deadline = time.ticks_add(time.ticks_ms(), int(wait_timeout * 1000))
        while True:
            if self.connection.check_receive():
                new_cmd = self.translate_command(self.connection.receive())
                if new_cmd:
                    result = new_cmd
                else:
                    console().write(f"ERROR on printer {self.friendly_name}: could not translate input", 'error')
                break
            if time.ticks_diff(deadline, time.ticks_ms()) <= 0:
                break
        return result

    def check_receive_commands(self) -> bool:
        return self.connection.check_receive()
        
    def send_response(self, response: dict[str, str]):
        new_response = self.translate_response(response)
        if new_response:
            self.connection.send(new_response)
        else:
            console().write(f"ERROR on printer {self.friendly_name}: could not translate command {response.get('command', '<Undefined>')}", 'error')

    def update(self):
        pass

    def get_plugin_status(self, response: dict[str, str]):
        response['friendly_name'] = self.friendly_name
        response['comm'] = self.connection.internal_name if self.connection else 'None'

    def translate_command(self, message: bytes) -> dict[str, str] | None:
        return None
    
    def translate_response(self, response: dict[str, str]) -> bytes | None:
        return None
    
    @staticmethod
    def make_from_config(config_data: dict[str, str], connection: IJCI_Base) -> IJP_Base:
        return IJP_Base(connection)

class IJP_Null: # Alias
    @staticmethod
    def make_from_config(config_data: dict[str, str], connection: IJCI_Base | None = None) -> IJP_Base:
        conn = IJCI_Null.make_from_config({})
        result = IJP_Base(conn)
        result.friendly_name = 'Null'
        return result

class IJP_Text_Based(IJP_Base):
    def __init__(self, connection: IJCI_Base, seperator: str | None = None):
        super().__init__(connection)
        self.seperator = seperator
        self.friendly_name = "Base_Placeholder_Text_Based"

    def get_plugin_status(self, response: dict[str, str]):
        super().get_plugin_status(response)
        response['seperator'] = self.seperator if self.seperator else 'None'

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
    
    @staticmethod
    def make_from_config(config_data: dict[str, str], connection: IJCI_Base) -> IJP_Text_Based: # Not that this one is ever useful...
        seperator = config_data.get('seperator', None)
        return IJP_Text_Based(connection, seperator)
        
class IJP_Text_Based_Direct(IJP_Base):
    # Directly takes IFS Jacker internal commands, and relays IFS Jacker internal responses.
    # This is intended for use with custom printers / custom integrations into other printers,
    # as it is likely cleaner than trying to emulate an AD5X. It can also be used to chain IFS
    # Jackers together.
    def __init__(self, connection: IJCI_Base):
        super().__init__(connection)
        self.friendly_name = 'Direct_IJ_Command'

    def translate_command(self, message: bytes) -> dict[str, str] | None:
        return command_str_to_dict(str(message, 'utf-8'))
    
    def translate_response(self, response: dict[str, str]) -> bytes | None:
        result = command_dict_to_str(response)
        if result == None:
            return None
        else:
            return result.encode('utf-8')
    
    @staticmethod
    def make_from_config(config_data: dict[str, str], connection: IJCI_Base) -> IJP_Text_Based_Direct:
        return IJP_Text_Based_Direct(connection)