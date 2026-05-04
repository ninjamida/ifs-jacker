# RGB LED output.
#
# Config params:
#  pin_(color) - Pin to use for a color (any pin may be omitted to not write that channel)
#  frequency - Output frequency for all colors
#  frequency_(color) - Specify frequency for a particular color
#  initial_state - State to set initially for all colors
#  initial_state_(color) - State to set initially for a particular color (0-255)
#  state_on_timeout - State to set on timeout. This can be a 32-bit value (red is lowest 8 bits) or none (leave unchanged).
#
# Commands:
#  F2 (get status) - Includes "red: X red_frequency: X etc" in the response. This is the last set value (0 - 255)
#  F3 (set all) - Sets power of all channels. Powers are specified by L value, as a 32 bit value (red is lowest 8 bits, white is highest), frequency optionally supplied by S value (sets one value for all channels). Can pass -1 for L value if trying to set only frequency.
#  F4 (set channel) - Sets power of one channel. Power is specified by L value (0 - 255), channel is specified by S value (r = 0, w = 3)
#  F5 (set freq) - Sets frequency of one channel. Frequency is specified by L value, channel is specified by S value (r = 0, w = 3)
#
# Status code: All channels packed into a 32-bit value (red is lowest 8 bits, white is highest)

from peripheral import IJ_Peripheral
from machine import Pin, PWM
from comm import _IJ_Comm_Abstract

COLOR_NAMES = ['red', 'green', 'blue', 'white']

class IJP_RGB_LED(IJ_Peripheral):
    def __init__(self, pins: list[int | None], frequencies: list[int | None] = [None] * 4, initial_states: list[int | None] = [None] * 4):
        super().__init__()

        self.identifier = f'RGB LED'
        self.all_pins: list[PWM | None] = []
        self.all_pin_ids: list[int] = [] # Order / gaps don't matter for this one
        for i, pin_id in enumerate(pins):
            if pin_id is None:
                self.all_pins.append(None)
            else:
                initial_state = initial_states[i]
                frequency = frequencies[i]
                if initial_state is None:
                    initial_state = 0
                else:
                    initial_state = int(initial_state * 255 / 65535)
                if frequency is None:
                    frequency = 2000
                self.all_pins.append(PWM(Pin(pin_id), duty_u16=initial_state, freq=frequency))
                self.all_pin_ids.append(pin_id)

        self.state_on_timeout: int | None = 0

    def handle_command(self, f=0, l=0, s=0, params=[]) -> str:
        if f == 2:
            elements = ['F2 peripheral ok.']

            for i, name in enumerate(COLOR_NAMES):
                pin = self.all_pins[i]
                if pin is None:
                    elements += [f'{name}: 0 {name}_frequency: 0']
                else:
                    elements += [f'{name}: {int(pin.duty_u16() / 65535 * 255)}']
                    elements += [f'{name}_frequency: {pin.freq()}']
            return ' '.join(elements)
        
        if f == 3:
            if s != 0:
                for pin in self.all_pins:
                    if pin is not None:
                        pin.freq(s)
            if l >= 0:
                self.set_state_from_packed(l)

            elements = ['F3 peripheral ok.']
            
            for i, name in enumerate(COLOR_NAMES):
                pin = self.all_pins[i]
                if pin is None:
                    elements += [f'{name}: 0']
                    if s != 0:
                        elements += ['{name}_frequency: 0']
                else:
                    elements += [f'{name}: {int(pin.duty_u16() / 65535 * 255)}']
                    if s != 0:
                        elements += [f'{name}_frequency: {pin.freq()}']
            
            return ' '.join(elements)

        if f == 4:
            elements = ['F4 peripheral ok.']
            if s >= 0 and s <= 3:
                pin = self.all_pins[s]
                if pin is not None:
                    pin.duty_u16(int(l / 255 * 65535))
                    elements += [f'{COLOR_NAMES[s]}: {int(pin.duty_u16() * 255 / 65535)}']
                else:
                    elements += [f'{COLOR_NAMES[s]}: 0']
            else:
                elements += ['Bad channel index']
            
            return ' '.join(elements)

        if f == 5:
            elements = ['F5 peripheral ok.']
            if s >= 0 and s <= 3:
                pin = self.all_pins[s]
                if pin is not None:
                    pin.freq(l)
                    elements += [f'{COLOR_NAMES[s]}_frequency: {pin.freq()}']
                else:
                    elements += [f'{COLOR_NAMES[s]}_frequency: 0']
            else:
                elements += ['Bad channel index']
            
            return ' '.join(elements)
            

        return super().handle_command(f, l, s, params)
    
    def set_state_from_packed(self, packed_state: int):
        for i in range(4):
            pin = self.all_pins[i]
            if pin:
                pin.duty_u16(int(((packed_state >> (i * 8)) & 0xFF) / 255 * 65535))

    def get_state_packed(self) -> int:
        result = 0
        for i in reversed(range(4)):
            pin = self.all_pins[i]
            if pin:
                result = (result << 8) | max(0, min(255, int(pin.duty_u16() * 255 / 65535)))
            else:
                result <<= 8
        return result
    
    def get_status_info(self) -> str:
        elements = []
        for i, pin in enumerate(self.all_pins):
            if pin:
                elements.append(f'{COLOR_NAMES[i]}: {int(pin.duty_u16() * 255 / 65535)}')
            else:
                elements.append(f'{COLOR_NAMES[i]}: 0')
        return ' '.join(f'{self.short_identifier}_{element}' for element in elements)

    def shutdown(self):
        for pin in self.all_pins:
            if pin is not None:
                pin.duty_u16(0)
                pin.deinit()
        for pin_id in self.all_pin_ids:
            Pin(pin_id, Pin.OUT, value=0)

    def timeout(self):
        if self.state_on_timeout is not None:
            self.set_state_from_packed(self.state_on_timeout)

    @staticmethod
    def create(config_data: dict[str, str], all_comms: list[_IJ_Comm_Abstract]):
        pins = []
        freqs = []
        states = []

        default_freq = config_data.get('frequency', 2000)
        default_state = config_data.get('initial_state', 0)

        for i in range(4):
            pin_id = config_data.get(f'pin_{COLOR_NAMES[i]}', None)
            if pin_id is not None: pin_id = int(pin_id)

            freq = int(config_data.get(f'frequency_{COLOR_NAMES[i]}', default_freq))
            state = int(config_data.get(f'initial_state_{COLOR_NAMES[i]}', default_state))

            pins += [pin_id]
            freqs += [freq]
            states += [state]

        result = IJP_RGB_LED(pins, freqs, states)

        state_on_timeout = config_data.get('state_on_timeout', 0)
        if state_on_timeout == 'none':
            result.state_on_timeout = None
        else:
            result.state_on_timeout = int(state_on_timeout)

        return result