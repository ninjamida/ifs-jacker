# GPIO input or output (digital pin).
#
# Config params:
#  output - Specifies if the pin is an output (true) or input (false)
#  pin - Specifies the pin ID to use
#  default_state - Specifies the initial state (output) or fallback state when not connected (input) of the pin
#  
#  
# Commands:
#  F2 (get status) - Includes "pin_state: 0" or "pin_state: 1" in the response.
#  F3 (set state)  - Output pin only. Sets the current state of the pin (L0 low, L1 high)
#
# Status code: Returns the state of the pin.

from peripheral import IJ_Peripheral
from machine import Pin
from comm import _IJ_Comm_Abstract

class IJP_Digital_Pin(IJ_Peripheral):
    def __init__(self, pin_id: int, default_state: int, is_output: bool):
        super().__init__()

        self.identifier = f'Digital Pin {pin_id} '
        self.is_output = is_output

        if is_output:
            self.identifier += 'Output'
            self.pin = Pin(pin_id, Pin.OUT, value=default_state)
        else:
            self.identifier += 'Input'
            self.pin = Pin(pin_id, Pin.IN, pull=default_state)

        self.state_on_timeout: bool | None = False
        
        self.report_in_F13 = not is_output
        self.report_in_Z4 = self.report_in_F13

    def handle_command(self, f=0, l=0, s=0) -> str:
        if f == 2:
            return f"F2 peripheral ok. pin_state: {self.pin.value()}"
        if f == 3:
            if self.is_output:
                self.pin.value(l != 0)
                return f"F3 peripheral ok. Pin set {"low" if l == 0 else "high"}"
            else:
                return "F3 peripheral ok. Cannot set input pin"
        return super().handle_command(f, l, s)

    def get_status_code(self) -> int:
        return self.pin.value()
    
    def timeout(self):
        if self.is_output and self.state_on_timeout is not None:
            self.pin.value(self.state_on_timeout)
    
    @staticmethod
    def create(config_data: dict[str, str], all_comms: list[_IJ_Comm_Abstract]):
        is_output = config_data.get('output', 'false') == 'true'

        pin_id = int(config_data['pin'])

        default_state = config_data.get('default_state', None)
        if is_output:
            default_state = 1 if default_state == 'true' else 0
            result = IJP_Digital_Pin(pin_id, default_state, True)
        else:
            default_state = Pin.PULL_UP if default_state == 'true' else Pin.PULL_DOWN
            result = IJP_Digital_Pin(pin_id, default_state, False)

        state_on_timeout = config_data.get('state_on_timeout', 'true')
        if state_on_timeout == 'none':
            result.state_on_timeout = None
        else:
            result.state_on_timeout = state_on_timeout == 'true'

        return result
