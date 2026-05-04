# GPIO analog input.
#
# Config params:
#  pin - Specifies the pin ID to use.
#  read_period - Specifies how often to sample the pin. If zero, it is sampled on-demand.
#  sample_count - How many samples to retain (and return an average of). Only works if read_period is nonzero.
#  sample_median - If true, the median of the samples is returned. Otherwise, the mean is returned.
#
# Commands:
#  F2 (get status) - Includes "pin_state: X" in the response
#
# Status code: The reading of the pin (with averaging / read period applied as necessary)

from peripheral import IJ_Peripheral
from machine import Pin, ADC
from comm import _IJ_Comm_Abstract
import time

class IJP_Analog_Pin(IJ_Peripheral):
    def __init__(self, pin_id: int, read_period: float = 0, sample_count: int = 1, sample_median: bool = False):
        super().__init__()

        self.identifier = f'Analog Pin {pin_id}'
        self.pin = ADC(Pin(pin_id))

        self.read_delay = int(read_period * 1000)
        self.samples = [0] * max(sample_count, 1)
        self.sample_median = sample_median

        self.next_sample_time = time.ticks_ms()
        self.is_first_update = True

    def handle_command(self, f=0, l=0, s=0, params=[]) -> str:
        if f == 2:
            return f"F2 peripheral ok. pin_state: {self.get_value()}"
        return super().handle_command(f, l, s, params)
    
    def get_status_info(self) -> str:
        return f'{self.short_identifier}_value: {self.get_value()}'

    def get_value(self) -> int:
        if self.read_delay == 0:
            return self.pin.read_u16()
        elif len(self.samples) == 1:
            return self.samples[0]
        elif self.sample_median:
            sorted_samples = self.samples.copy()
            sorted_samples.sort()
            target_item = len(sorted_samples) // 2
            if len(sorted_samples) % 2 == 0:
                return (sorted_samples[target_item] + sorted_samples[target_item - 1]) // 2
            else:
                return sorted_samples[target_item]
        else:
            return int(sum(self.samples) / len(self.samples))

    def update(self):
        if self.read_delay > 0:
            if self.is_first_update or time.ticks_diff(self.next_sample_time, time.ticks_ms()) < 0:
                new_sample = self.pin.read_u16()
                if self.is_first_update:
                    self.is_first_update = False
                    self.samples = [new_sample] * len(self.samples)
                    self.next_sample_time = time.ticks_add(time.ticks_ms(), self.read_delay)
                else:
                    self.samples.pop(0)
                    self.samples.append(new_sample)
                    self.next_sample_time = time.ticks_add(self.next_sample_time, self.read_delay)

    @staticmethod
    def create(config_data: dict[str, str], all_comms: list[_IJ_Comm_Abstract]):
        pin_id = int(config_data['pin'])
        read_period = float(config_data.get('read_period', 0))
        sample_count = int(config_data.get('sample_count', 1))
        sample_median = config_data.get('sample_median', 'false') == 'true'
        return IJP_Analog_Pin(pin_id, read_period, sample_count, sample_median)
