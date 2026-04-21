# DHT11 / DHT22 input.
#
# Config params:
#  pin - Specifies the pin ID to use.
#  read_period - Specifies how often to sample the pin. Not recommended to reduce under 2 seconds.
#
# Commands:
#  F2 (get status) - Includes "temperature: X humidity: X" in the response
#
# Status code: The last temperature reading of the pin

from peripheral import IJ_Peripheral
from machine import Pin
from dht import DHT11, DHT22
from comm import _IJ_Comm_Abstract
import time

class IJP_DHT(IJ_Peripheral):
    def __init__(self, sensor: DHT11 | DHT22):
        super().__init__()
        self.sensor = sensor
        self.temperature = 0.0
        self.humidity = 0.0

        self.reading_delay = 2 * 1000
        self.delay_timeout = time.ticks_ms()

        self.prev_reading_error = False

    def handle_command(self, f=0, l=0, s=0) -> str:
        if f == 2:
            return f"F2 peripheral ok. temperature: {self.temperature} humidity: {self.humidity}"
        return super().handle_command(f, l, s)
    
    def get_status_code(self) -> int:
        return int(self.temperature * 100)
    
    def update(self):
        if time.ticks_diff(self.delay_timeout, time.ticks_ms()) < 0:
            try:
                self.sensor.measure()

                self.temperature = self.sensor.temperature()
                self.humidity = self.sensor.humidity()

                self.prev_reading_error = False
            except:
                if self.prev_reading_error:
                    self.temperature = 0.0
                    self.humidity = 0.0

            self.delay_timeout = time.ticks_add(time.ticks_ms(), self.reading_delay)

    @staticmethod
    def create(config_data: dict[str, str], all_comms: list[_IJ_Comm_Abstract]):
        pin_id = int(config_data['pin'])
        if config_data.get('kind', 'dht11') == 'dht22':
            sensor = DHT22(Pin(pin_id))
        else:
            sensor = DHT11(Pin(pin_id))
        result = IJP_DHT(sensor)
        read_period = float(config_data.get('read_period', 2))
        result.reading_delay = int(read_period * 1000)
        return result
