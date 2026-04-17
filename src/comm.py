from machine import UART, Pin
from util import decode_valid_bytes
from console import get_console
import time, machine, _thread

DEFAULT_BLOCK_SEND_DURATION = int(0.2 * 1000)
DEFAULT_INTER_CHAR_TIMEOUT = int(0.005 * 1000) # Will always allow one more iteration after last data was received regardless of timeout
UNBLOCK_SEND_UPDATE_TIME = int(300 * 1000)

DEFAULT_UART_BAUD = 115200
DEFAULT_UART_BITS = 8
DEFAULT_UART_PARITY = None
DEFAULT_UART_STOP_BITS = 1

# SIO Base and GPIO offsets
SIO_BASE = 0xd0000000
GPIO_OUT_SET = SIO_BASE + 0x14
GPIO_OUT_CLR = SIO_BASE + 0x18

class IJ_Comm_Manager:
    def __init__(self):
        self.comm_list = []
        self.peripherals = []
        self.started = False
        self.terminate = False
        self.finished = False
        self.console = get_console()

        self.core: IJ_Core = None # type: ignore

    def start_thread(self):
        _thread.start_new_thread(self.run, ())

    def run(self):
        self.started = True
        update_comm_index = 0
        update_peripheral_index = 0
        while not self.terminate:
            self.console.flush()
            try:
                if len(self.comm_list) > 0:
                    if update_comm_index >= len(self.comm_list):
                        update_comm_index = 0
                    else:
                        self.comm_list[update_comm_index].update()
                        update_comm_index += 1

                if len(self.peripherals) > 0:
                    if update_peripheral_index >= len(self.peripherals):
                        update_peripheral_index = 0
                    else:
                        if self.peripherals[update_peripheral_index].use_primary_thread:
                            self.peripherals[update_peripheral_index].update()
                        update_peripheral_index += 1
            except KeyboardInterrupt:
                self.terminate = True
            except Exception as e:
                self.console.print_exception(e, 'comms')

            if self.core.terminate:
                self.terminate = True

        for comm_interface in self.comm_list:
            try:
                comm_interface.shutdown()
            except Exception as e:
                self.console.print_exception(e)
        self.finished = True

class _IJ_Comm_Abstract:
    def __init__(self):
        self._send_queue: list[str] = []
        self._receive_queue: list[str] = []
        self._receive_buffer: list[bytes] = []
        self._send_lock = _thread.allocate_lock()
        self._receive_lock = _thread.allocate_lock()

        self.inter_char_timeout = DEFAULT_INTER_CHAR_TIMEOUT

        self.send_block_after_send_time = 0
        self.send_block_while_incoming = False
        self.unblock_send_on_receive = True # Only affects time-based blocks, not while-incoming blocks if further data is coming

        self._send_unblock_time = time.ticks_ms()
        self._receive_timeout_time = time.ticks_ms()

    def send(self, data: str):
        self._send_lock.acquire()
        self._send_queue.append(data)
        self._send_lock.release()

    def check_receive(self) -> bool:
        return len(self._receive_queue) > 0

    def receive(self) -> str:
        if len(self._receive_queue) > 0:
            if self._receive_lock.acquire(0):
                result = self._receive_queue.pop(0)
                self._receive_lock.release()
                return result

        return ''

    def block_send(self, duration: int | None = None):
        if duration is None:
            self._send_unblock_time = time.ticks_add(time.ticks_ms(), self.send_block_after_send_time)
        else:
            self._send_unblock_time = time.ticks_add(time.ticks_ms(), duration)

    def update(self):
        # Update send unblock time to current time periodically to eliminate risk of overflow
        diff = time.ticks_diff(self._send_unblock_time, time.ticks_ms())
        if diff < -UNBLOCK_SEND_UPDATE_TIME:
            self._send_unblock_time = time.ticks_ms()

        if len(self._send_queue) > 0 and diff < 0:
            if not self.send_block_while_incoming or (len(self._receive_buffer) == 0 and not self._comm_check_receive()):
                self._send_next_queued_command()

        if self._comm_check_receive():
            new_data = self._comm_receive()
            if len(new_data) > 0:
                self._receive_buffer.append(new_data)
                self._receive_timeout_time = time.ticks_add(time.ticks_ms(), self.inter_char_timeout)
        elif len(self._receive_buffer) > 0 and time.ticks_diff(self._receive_timeout_time, time.ticks_ms()) < 0:
            data = decode_valid_bytes(b''.join(self._receive_buffer))
            self._receive_buffer = []
            self._receive_lock.acquire()
            self._receive_queue.append(data)
            self._receive_lock.release()
            if self.unblock_send_on_receive:
                self._send_unblock_time = time.ticks_ms()

    def initialize(self):
        pass

    def shutdown(self):
        pass

    def _send_next_queued_command(self):
        if self._send_lock.acquire(0):
            send_data = self._send_queue.pop(0)
            self._send_lock.release()
            self._comm_send(send_data.encode('utf-8'))
            if self.send_block_after_send_time > 0:
                self.block_send()

    def _comm_send(self, data: bytes):
        pass

    def _comm_check_receive(self) -> bool:
        return False

    def _comm_receive(self) -> bytes:
        return bytes()


class IJ_Comm_UART(_IJ_Comm_Abstract):
    def __init__(self, uart_instance: int, tx_pin: int, rx_pin: int, baud:int=DEFAULT_UART_BAUD, bits:int=DEFAULT_UART_BITS,
                 parity:int|None=DEFAULT_UART_PARITY, stop_bits:int=DEFAULT_UART_STOP_BITS):
        super().__init__()
        self.uart = UART(
            uart_instance, baudrate=baud, bits=bits, parity=parity, stop=stop_bits,
            tx=tx_pin, rx=rx_pin
            )

    def _comm_send(self, data: bytes):
        self.uart.write(data)
        self.uart.flush()

    def _comm_check_receive(self) -> bool:
        return self.uart.any() > 0

    def _comm_receive(self) -> bytes:
        result = self.uart.read()
        if result:
            return result
        else:
            return bytes()

    @staticmethod
    def make_from_config(data: dict[str, str]):
        parity = data.get('parity', DEFAULT_UART_PARITY)
        if parity is None or parity == 'None':
            parity = None
        else:
            parity = int(parity)

        result = IJ_Comm_UART(
            uart_instance = int(data['uart_instance']),
            tx_pin = int(data['tx_pin']),
            rx_pin = int(data['rx_pin']),
            baud = int(data.get('baud', DEFAULT_UART_BAUD)),
            bits = int(data.get('bits', DEFAULT_UART_BITS)),
            parity = parity,
            stop_bits = int(data.get('stop_bits', DEFAULT_UART_STOP_BITS))
        )
        return result

class IJ_Comm_UART_EN(_IJ_Comm_Abstract):
    def __init__(self, uart_instance: int, tx_pin: int, rx_pin: int, en_pin: int, en_write_state: bool = True, baud:int=115200, bits:int=8, parity:int|None=None, stop_bits:int=1):
        super().__init__()
        self.uart = UART(
            uart_instance, baudrate=baud, bits=bits, parity=parity, stop=stop_bits,
            tx=tx_pin, rx=rx_pin
            )
        self.en_write_state = en_write_state
        self.en_pin = Pin(en_pin, Pin.OUT, value=not en_write_state)
        self.send_block_after_send_time = DEFAULT_BLOCK_SEND_DURATION
        self.send_block_while_incoming = True

    def _comm_send(self, data: bytes):
        self.en_pin.value(self.en_write_state)
        self.uart.write(data)
        self.uart.flush()
        self.en_pin.value(not self.en_write_state)

    def _comm_check_receive(self) -> bool:
        return self.uart.any() > 0

    def _comm_receive(self) -> bytes:
        result = self.uart.read()
        if result:
            return result
        else:
            return bytes()

    @staticmethod
    def make_from_config(data: dict[str, str]):
        parity = data.get('parity', DEFAULT_UART_PARITY)
        if parity is None or parity == 'None':
            parity = None
        else:
            parity = int(parity)

        result = IJ_Comm_UART_EN(
            uart_instance = int(data['uart_instance']),
            tx_pin = int(data['tx_pin']),
            rx_pin = int(data['rx_pin']),
            en_pin = int(data['en_pin']),
            en_write_state = data.get('en_write_state', 'true') == 'true',
            baud = int(data.get('baud', DEFAULT_UART_BAUD)),
            bits = int(data.get('bits', DEFAULT_UART_BITS)),
            parity = parity,
            stop_bits = int(data.get('stop_bits', DEFAULT_UART_STOP_BITS))
        )
        return result

class IJ_Comm_UART_EN_Multi(_IJ_Comm_Abstract): # Don't use directly. Use IJ_Comm_UART_EN_Multi_Client instead
    def __init__(self, uart_instance: int, tx_pin: int, rx_pin: int, en_write_state: bool = True, baud:int=115200, bits:int=8, parity:int|None=None, stop_bits:int=1):
        super().__init__()
        self.uart = UART(
            uart_instance, baudrate=baud, bits=bits, parity=parity, stop=stop_bits,
            tx=tx_pin, rx=rx_pin
            )
        self.en_pins = []
        self.en_pin_ids = []
        self.send_block_after_send_time = DEFAULT_BLOCK_SEND_DURATION
        self.send_block_while_incoming = True

        self._queue_en_pins = []
        self._last_used_en_pin = None

        self.en_enable_register = GPIO_OUT_SET if en_write_state else GPIO_OUT_CLR
        self.en_disable_register = GPIO_OUT_CLR if en_write_state else GPIO_OUT_SET
        self.all_pins_mask = 0

    def initialize(self):
        self.all_pins_mask = 0
        for pin_id in self.en_pin_ids:
            self.all_pins_mask |= 1 << pin_id
        if len(self.en_pin_ids) > 0:
            pin_bit = 1 << self.en_pin_ids[0]
            exclude_pin_bits = self.all_pins_mask ^ pin_bit
            machine.mem32[self.en_disable_register] = pin_bit
            machine.mem32[self.en_enable_register] = exclude_pin_bits

    def send(self, data: str, en_pin: Pin | None = None):
        if en_pin == None:
            if self._last_used_en_pin == None:
                return
            else:
                en_pin = self._last_used_en_pin

        self._last_used_en_pin = en_pin
        self._send_lock.acquire()
        self._send_queue.append(data)
        self._queue_en_pins.append(en_pin)
        self._send_lock.release()

    def _send_next_queued_command(self):
        if self._send_lock.acquire(0):
            send_data = self._send_queue.pop(0)
            en_pin = self._queue_en_pins.pop(0)
            self._send_lock.release()
            self._comm_send(send_data.encode('utf-8'), en_pin)
            if self.send_block_after_send_time > 0:
                self.block_send()

    def _comm_send(self, data: bytes, en_pin: Pin):
        pin_bit = 1 << self.en_pin_ids[self.en_pins.index(en_pin)]
        exclude_pin_bits = self.all_pins_mask ^ pin_bit
        machine.mem32[self.en_disable_register] = exclude_pin_bits
        machine.mem32[self.en_enable_register] = pin_bit
        self.uart.write(data)
        self.uart.flush()
        machine.mem32[self.en_disable_register] = pin_bit
        machine.mem32[self.en_enable_register] = exclude_pin_bits
        self._last_used_en_pin = en_pin

    def _comm_check_receive(self) -> bool:
        return self.uart.any() > 0

    def _comm_receive(self) -> bytes:
        result = self.uart.read()
        if result:
            return result
        else:
            return bytes()

    def make_child(self, data: dict[str, str]):
        en_pin = int(data['en_pin'])
        return IJ_Comm_UART_EN_Multi_Client(self, en_pin)

    @staticmethod
    def make_from_config(data: dict[str, str]):
        parity = data.get('parity', DEFAULT_UART_PARITY)
        if parity is None or parity == 'None':
            parity = None
        else:
            parity = int(parity)

        result = IJ_Comm_UART_EN_Multi(
            uart_instance = int(data['uart_instance']),
            tx_pin = int(data['tx_pin']),
            rx_pin = int(data['rx_pin']),
            en_write_state = data.get('en_write_state', 'true') == 'true',
            baud = int(data.get('baud', DEFAULT_UART_BAUD)),
            bits = int(data.get('bits', DEFAULT_UART_BITS)),
            parity = parity,
            stop_bits = int(data.get('stop_bits', DEFAULT_UART_STOP_BITS))
        )
        return result

class IJ_Comm_UART_EN_Multi_Client:
    def __init__(self, parent: IJ_Comm_UART_EN_Multi, en_pin: int):
        self.parent = parent
        self.en_pin = Pin(en_pin, Pin.OUT)
        parent.en_pins.append(self.en_pin)
        parent.en_pin_ids.append(en_pin)

    def send(self, data: str):
        self.parent.send(data, self.en_pin)

    def check_receive(self) -> bool:
        return self.parent.check_receive()

    def receive(self) -> str:
        return self.parent.receive()

    def update(self):
        pass

    def initialize(self):
        pass

    def shutdown(self):
        pass

    def block_send(self, duration: int | None = None):
        self.parent.block_send(duration)