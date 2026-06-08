# DHT11 / DHT22 input.
# Due to slow response, these are ONLY read when not awaiting MMU response.
#
# Config params:
#  pin - Specifies the pin ID to use.
#  read_period - Specifies how often to sample the pin. Not recommended to reduce under 2 seconds.
#
# Commands:
#  F2 (get status) - Includes "temperature: X humidity: X" in the response

from peripheral import IJ_Peripheral
from machine import Pin
from comm import _IJ_Comm_Abstract
from PicoDHT22 import PicoDHT22
import time
from console import get_console

class IJP_DHT(IJ_Peripheral):
    def __init__(self, pin_id: int, smID: int, is_dht11: bool):
        super().__init__()

        self.identifier = 'DHT11' if is_dht11 else 'DHT22'

        self.pin = Pin(pin_id, Pin.IN, Pin.PULL_UP)
        self.pio_index = smID
        self.sensor = PicoDHT22(self.pin, dht11=is_dht11, smID=self.pio_index)

        self.temperature = 0.0
        self.humidity = 0.0

        self.reading_delay = 2 * 1000
        self.delay_timeout = time.ticks_ms() + self.reading_delay

        self.prev_reading_error = False

    def handle_command(self, f=0, l=0, s=0, params=[]) -> str:
        if f == 2:
            return f"F2 peripheral ok. temperature: {self.temperature} humidity: {self.humidity}"
        return super().handle_command(f, l, s, params)
    
    def get_status_info(self) -> str:
        return f'{self.short_identifier}_temperature: {self.temperature} {self.short_identifier}_humidity: {self.humidity}'
    
    def update(self, core_idle: bool):
        if core_idle and time.ticks_diff(self.delay_timeout, time.ticks_ms()) < 0:
            try:
                temp, humidity = self.sensor.read()
                if temp is None:
                    self.handle_error_data()
                else:
                    self.temperature = temp
                    self.humidity = humidity
            except:
                self.handle_error_data()

            self.delay_timeout = time.ticks_add(time.ticks_ms(), self.reading_delay)

    def handle_error_data(self):
        if self.prev_reading_error:
            self.temperature = -1.0
            self.humidity = -1.0
        else:
            self.prev_reading_error = True

    @staticmethod
    def create(config_data: dict[str, str], all_comms: list[_IJ_Comm_Abstract]):
        pin_id = int(config_data['pin'])
        sm_id = int(config_data['pio'])
        kind = config_data.get('kind', 'dht11')
        result = IJP_DHT(pin_id, sm_id, kind != 'dht22')
        read_period = float(config_data.get('read_period', 2))
        result.reading_delay = int(read_period * 1000)
        return result
