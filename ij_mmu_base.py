from ij_comm_base import IJCI_Base, IJCI_Null
from ij_command_conversion import command_dict_to_str, command_str_to_dict
from ij_console import console
import time

class IJM_Base:
    def __init__(self, connection: IJCI_Base):
        self.connection = connection
        self.command_response_wait_timeout = 1
        self.friendly_name = "Base_Placeholder"
        self.out_cmd_queue: list[dict[str, str]] = []

    def get_channel_count(self) -> int:
        return 0
    
    def receive_data(self, wait_timeout: float = 0) -> dict[str, str] | None:
        if len(self.out_cmd_queue) > 0:
            return self.out_cmd_queue.pop(0)

        result = None
        deadline = time.ticks_add(time.ticks_ms(), int(wait_timeout * 1000))
        while True:
            if self.connection.check_receive():
                new_response = self.translate_response(self.connection.receive())
                if new_response:
                    result = new_response
                else:
                    console().write(f"ERROR on MMU {self.friendly_name}: could not translate input", 'error')
                break
            if time.ticks_diff(deadline, time.ticks_ms()) <= 0:
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
            console().write(f"ERROR on MMU {self.friendly_name}: could not translate command {command.get('command', '<Undefined>')}", 'error')
        
        return None
        
    def update(self):
        pass

    def get_plugin_status(self, response: dict[str, str]):
        response['friendly_name'] = self.friendly_name
        response['comm'] = self.connection.internal_name if self.connection else 'None'
        response['channel_count'] = str(self.get_channel_count())

    def translate_command(self, command: dict[str, str]) -> bytes | None:
        return None
    
    def translate_response(self, message: bytes) -> dict[str, str] | None:
        return None
    
    @staticmethod
    def make_from_config(config_data: dict[str, str], connection: IJCI_Base, key_prefix: str = '', load_mmu_func = None) -> IJM_Base:
        return IJM_Base(connection)
    
class IJM_Null: # Alias    
    @staticmethod
    def make_from_config(config_data: dict[str, str], connection: IJCI_Base | None = None, key_prefix: str = '', load_mmu_func = None) -> IJM_Base:
        conn = IJCI_Null.make_from_config({})
        result = IJM_Base(conn)
        result.friendly_name = 'Null'
        return result
    
class IJM_Text_Based(IJM_Base):
    def __init__(self, connection: IJCI_Base, seperator: str | None = None):
        super().__init__(connection)
        self.seperator = seperator
        self.friendly_name = "Base_Placeholder_Text_Based"

    def get_plugin_status(self, response: dict[str, str]):
        super().get_plugin_status(response)
        response['seperator'] = self.seperator if self.seperator else 'None'
    
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
            
    @staticmethod
    def make_from_config(config_data: dict[str, str], connection: IJCI_Base, key_prefix: str = '', load_mmu_func = None) -> IJM_Text_Based: # Not that this one is ever useful...
        seperator = config_data.get(key_prefix + 'seperator', None)
        return IJM_Text_Based(connection, seperator)
    
class IJM_Text_Based_Direct(IJM_Base):
    # Directly takes IFS Jacker internal commands, and relays IFS Jacker internal responses.
    # This is intended for use with custom printers / custom integrations into other printers,
    # as it is likely cleaner than trying to emulate an AD5X. It can also be used to chain IFS
    # Jackers together.
    def __init__(self, connection: IJCI_Base):
        super().__init__(connection)
        self.friendly_name = 'Direct_IJ_Command'
        self.cached_channel_count: int | None = None

    def translate_command(self, message: bytes) -> dict[str, str] | None:
        return command_str_to_dict(str(message, 'utf-8'))
    
    def translate_response(self, response: dict[str, str]) -> bytes | None:
        result = command_dict_to_str(response)
        if result == None:
            return None
        else:
            return result.encode('utf-8')
        
    def get_channel_count(self) -> int:
        if not self.cached_channel_count:
            channel_count_response = self.send_command({'command': 'ij_get_channel_count'}, True)
            if channel_count_response:
                self.cached_channel_count = int(channel_count_response.get('channels', 0))
            else:
                return 0
        return self.cached_channel_count
    
    @staticmethod
    def make_from_config(config_data: dict[str, str], connection: IJCI_Base, key_prefix: str = '', load_mmu_func = None) -> IJM_Text_Based_Direct:
        result = IJM_Text_Based_Direct(connection)
        channel_count_raw = config_data.get(key_prefix + 'channels', None)
        if channel_count_raw:
            result.cached_channel_count = int(channel_count_raw)
        return result