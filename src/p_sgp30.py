# SGP30 CO2 and TVOC sensor.
# 
# Config params:
# 
# Commands:
#  F2 (get status): Includes "co2: x tvoc: x" in the response.
#  F3 (check baseline): Reports "co2_baseline: x tvoc_baseline: x" in the response.

from comm import _IJ_Comm_Abstract
from peripheral import IJ_Peripheral
from machine import Pin, I2C
import uSGP30
import time
import console

SGP30_I2C_FREQUENCY = 400000
SGP30_UPDATE_DELAY = 1 * 1000
SGP30_RECORD_BASELINE_DELAY = 60 * 60 * 1000 # 1hr

class IJP_SGP30(IJ_Peripheral):
    def __init__(self, i2c_index: int, i2c_scl_pin: int, i2c_sda_pin: int, baseline_file: str | None = None):
        super().__init__()

        self.identifier = f'SGP30 {i2c_index}-{i2c_scl_pin}-{i2c_sda_pin}'

        self.i2c = I2C(i2c_index, scl=Pin(i2c_scl_pin, Pin.OUT), sda=Pin(i2c_sda_pin, Pin.OUT), freq=SGP30_I2C_FREQUENCY)
        self.sgp30 = uSGP30.SGP30(self.i2c)

        self.next_update_time = time.ticks_ms()
        self.next_record_baseline_time = time.ticks_add(time.ticks_ms(), SGP30_RECORD_BASELINE_DELAY)

        self.last_result_none = True

        if baseline_file:
            self.baseline_file = baseline_file
        else:
            self.baseline_file = f'sgp30_{i2c_index}_{i2c_scl_pin}_{i2c_sda_pin}'

        self.last_tvoc = 0
        self.last_co2 = 400

        try:
            with open(self.baseline_file, 'r') as f:
                lines = f.readlines()
                baseline_co2 = int(lines[0].strip())
                baseline_tvoc = int(lines[1].strip())
            self.sgp30.set_iaq_baseline(baseline_co2, baseline_tvoc)
        except:
            pass
    
    def handle_command(self, f=0, l=0, s=0, params=[]) -> str:
        if f == 2:
            return f"F2 peripheral ok. co2: {self.last_co2} tvoc: {self.last_tvoc}"
        if f == 3:
            baseline = self.sgp30.get_iaq_baseline()
            if baseline is None:
                baseline = [0, 0]
            return f"F3 periperhal ok. co2_baseline: {baseline[0]} tvoc_baseline: {baseline[1]}"
        return super().handle_command(f, l, s, params)

    def get_status_info(self) -> str:
        return f'{self.short_identifier}_co2: {self.last_co2} {self.short_identifier}_tvoc: {self.last_tvoc}'
    
    def update(self):
        if time.ticks_diff(self.next_update_time, time.ticks_ms()) < 0:
            measure_result = self.sgp30.measure_iaq()
            if measure_result is None:
                if self.last_result_none:
                    self.last_co2 = 400
                    self.last_tvoc = 0
                else:
                    self.last_result_none = True
            else:
                self.last_result_none = False
                self.last_co2 = measure_result[0]
                self.last_tvoc = measure_result[1]
            self.next_update_time = time.ticks_add(time.ticks_ms(), SGP30_UPDATE_DELAY)
        if time.ticks_diff(self.next_record_baseline_time, time.ticks_ms()) < 0:
            try:
                baseline = self.sgp30.get_iaq_baseline()
                if baseline is not None:
                    with open(self.baseline_file, 'w') as f:
                        f.write(f'{baseline[0]}\n{baseline[1]}')
            except Exception as e:
                console.get_console().print_exception(e, 'sgp30')
            self.next_record_baseline_time = time.ticks_add(time.ticks_ms(), SGP30_RECORD_BASELINE_DELAY)

    
    @staticmethod
    def create(config_data: dict[str, str], all_comms: list[_IJ_Comm_Abstract]):
        i2c_index = int(config_data['i2c_index'])
        i2c_scl_pin = int(config_data['scl_pin'])
        i2c_sda_pin = int(config_data['sda_pin'])
        baseline_file = config_data.get('baseline_file', None)
        return IJP_SGP30(i2c_index, i2c_scl_pin, i2c_sda_pin, baseline_file)