# Thermistor input.
#
# Config params:
#  (All params of analog pin peripheral)
#  beta - Beta value of the thermistor. If unsure try 3950.
#  r0 - Resistance value at reference temperature. If unsure try 100000.
#  t0 - Reference temperature (celcius). If unsure try 25.
#  rfixed - Fixed resistor resistance. If unsure try 100000.
#
# Commands:
#  F2 (get status) - Includes "temperature: X" in the response (eg "temperature: 23.18")

from comm import _IJ_Comm_Abstract
from p_analog_pin import IJP_Analog_Pin
import math

class IJP_Thermistor(IJP_Analog_Pin):
    def __init__(self, pin_id: int, read_period: float = 0, sample_count: int = 1, sample_median: bool = False):
        super().__init__(pin_id, read_period, sample_count, sample_median)
        self.beta = 3950
        self.r0_value = 100000
        self.t0_value = 298.15
        self.rf_value = 100000
        self.identifier = f'Thermistor {pin_id}'

    def handle_command(self, f=0, l=0, s=0, params=[]) -> str:
        if f == 2:
            return f"F2 peripheral ok. temperature: {self.get_value() / 100}"
        return super().handle_command(f, l, s, params)

    def get_value(self) -> int:
        raw_result = min(65534, max(super().get_value(), 2)) # Clamped to avoid potential divide by zero errors

        result = self.rf_value / (65535 / raw_result - 1)
        result = math.log(result / self.r0_value) / self.beta
        result += 1.0 / self.t0_value
        return int(((1.0 / result) - 273.15) * 100)
    
    def get_status_info(self) -> str:
        return f'{self.short_identifier}_temperature: {self.get_value() / 100}'

    @staticmethod
    def create(config_data: dict[str, str], all_comms: list[_IJ_Comm_Abstract]):
        pin_id = int(config_data['pin'])
        read_period = float(config_data.get('read_period', 0))
        sample_count = int(config_data.get('sample_count', 1))
        sample_median = config_data.get('sample_median', 'false') == 'true'
        result = IJP_Thermistor(pin_id, read_period, sample_count, sample_median)

        result.beta = float(config_data['beta'])
        result.r0_value = float(config_data['r0'])
        result.t0_value = float(config_data['t0']) + 273.15
        result.rf_value = float(config_data['rfixed'])

        return result