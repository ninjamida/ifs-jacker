# PWM output. Useful for fans etc. Will generally need to run via a MOSFET.
#
# Config params:
#  pin - The pin number to use
#  frequency - The output frequency
#  initial_power - The initial power level (duty cycle) to set to
#
# Commands:
#  F2 (get status) - Includes "power: X" in the response. This is the last set value (0 - 65535)
#  F3 (set power) - Sets power of PWM signal. Power is specified by L value, range is 0 to 65535. Frequency (in kHz) optionally specified by S value.
#
# Status code: The last set value (0 - 65535)

from peripheral import IJ_Peripheral
from machine import Pin, PWM
from comm import _IJ_Comm_Abstract

class IJP_PWM_Output(IJ_Peripheral):
    def __init__(self, pin_id: int, frequency: int, initial_power: int = 0):
        super().__init__()

        self.identifier = f'PWM Output {pin_id}'
        self.pin = PWM(Pin(pin_id), duty_u16=initial_power)
        self.pin.freq(frequency)
    
    def handle_command(self, f=0, l=0, s=0) -> str:
        if f == 2:
            return f"F2 peripheral ok. power: {self.pin.duty_u16()} frequency: {self.pin.freq()}"
        if f == 3:
            if s == 0:
                self.pin.duty_u16(l)
                return f"F3 peripheral ok. power: {self.pin.duty_u16()}"
            else:
                self.pin.freq(s)
                self.pin.duty_u16(l)
                return f"F3 peripheral ok. power: {self.pin.duty_u16()} frequency: {self.pin.freq()}"

        return super().handle_command(f, l, s)
    
    def get_status_code(self) -> int:
        return self.pin.duty_u16()
    
    def shutdown(self):
        self.pin.duty_u16(0)
        self.pin.deinit()

    @staticmethod
    def create(config_data: dict[str, str], all_comms: list[_IJ_Comm_Abstract]):
        pin_id = int(config_data['pin'])
        frequency = int(config_data['frequency'])
        initial_power = int(config_data.get('initial_power', 0))
        return IJP_PWM_Output(pin_id, frequency, initial_power)