from ij_comm_interfaces import IJCI_Null
import time

class IJM_Null:
    def __init__(self, connection: IJCI_Null):
        self.connection = connection
        self.command_response_wait_timeout = 1

    def get_channel_count(self) -> int:
        return 0

    def get_status(self) -> dict[str, str]:
        return {'global_state': 'ok', 'active_channel': '-1'}
    
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