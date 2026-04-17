# Random number generator output. Intended for testing / debugging purposes.
#
# Config params:
#  min - Minimum value (inclusive)
#  max - Maximum value (inclusive)
#  refresh - How often to refresh the saved random value
#
# Commands:
#  F2 (get status) - Includes "last_rng: X" in the response
#  F3 (get fresh random number) - Generates and returns a random number (seperate from the cached value)
#
# Status code: The last generated random number

from peripheral import IJ_Peripheral
from comm import _IJ_Comm_Abstract
import random, time

class IJP_RNG(IJ_Peripheral):
    def __init__(self):
        super().__init__()
        self.identifier = 'Random Number Generator'
        self.min = 0
        self.max = 99
        self.refresh = 1 * 1000
        self.refresh_time = time.ticks_ms()

        self.cached_random_value = 0

    def update(self):
        if time.ticks_diff(self.refresh_time, time.ticks_ms()) < 0:
            self.refresh_time = time.ticks_add(time.ticks_ms(), self.refresh)
            self.cached_random_value = random.randrange(self.min, self.max + 1)

    def handle_command(self, f=0, l=0, s=0) -> str:
        if f == 2:
            return f"F2 peripheral ok. last_rng: {self.cached_random_value}"
        if f == 3:
            return f'F3 peripheral ok. rng: {random.randrange(self.min, self.max + 1)}'
        return super().handle_command(f, l, s)

    def get_status_code(self) -> int:
        return self.cached_random_value

    @staticmethod
    def create(config_data: dict[str, str], all_comms: list[_IJ_Comm_Abstract]):
        result = IJP_RNG()
        result.min = int(config_data.get('min', 0))
        result.max = int(config_data.get('max', 99))
        result.refresh = int(float(config_data.get('refresh', 1)) * 1000)
        return result
