from machine import UART, Pin
from ij_console import console
import time
import _thread

class IJCI_Base:
    def __init__(self):
        self.friendly_name = 'Base Placeholder'
        self.internal_name = ''

        self.receive_buffer: list[bytes] = []
        self.receive_lock = _thread.allocate_lock()

        self.send_buffer: list[bytes] = []
        self.send_lock = _thread.allocate_lock()

    def send(self, message: bytes):
        self.send_lock.acquire()
        try:
            self.send_buffer.append(message)
        finally:
            self.send_lock.release()

    def check_receive(self) -> bool:
        return len(self.receive_buffer) > 0
    
    def receive(self, timeout: int = 0) -> bytes:
        deadline = time.ticks_add(time.ticks_ms(), timeout)
        while True:
            if len(self.receive_buffer) > 0:
                self.receive_lock.acquire()
                try:
                    return self.receive_buffer.pop(0)
                finally:
                    self.receive_lock.release()
            if time.ticks_diff(deadline, time.ticks_ms()) < 0:
                break
        return bytes()
    
    def update(self):
        pass

    def get_plugin_status(self, response: dict[str, str]):
        response['friendly_name'] = self.friendly_name
    
    @staticmethod
    def make_from_config(config_data: dict[str, str]) -> IJCI_Base:
        return IJCI_Base()
    
class IJCI_Null: # Alias
    @staticmethod
    def make_from_config(config_data: dict[str, str]) -> IJCI_Base:
        result = IJCI_Base()
        result.friendly_name = 'Null'
        result.internal_name = 'Null'
        return result
    
class IJCI_UART(IJCI_Base):
    def __init__(self, uart_channel: int, tx_pin: int, rx_pin: int, baud:int=115200, bits:int=8, parity:int|None=None, stop_bits:int=1):
        super().__init__()
        self.uart = UART(
            uart_channel, baudrate=baud, bits=bits, parity=parity, stop=stop_bits,
            tx=tx_pin, rx=rx_pin
            )
        self.receive_continue_timeout = int(0.02 * 1000)
        self.friendly_name = 'UART'

        self.current_buffer_deadline = time.ticks_ms()
        self.current_line_buffer = bytes()

        self.suspend_send_while_receiving = False
        self.minimum_delay_between_sends = 0
        self.next_send_time = time.ticks_ms()

    def update(self):
        self.handle_rx()
        if not self.suspend_send_while_receiving or (not self.uart.any() and len(self.current_line_buffer) == 0):
            self.handle_tx()

    def handle_tx(self):
        if len(self.send_buffer) > 0 and time.ticks_diff(self.next_send_time, time.ticks_ms()) < 0:
            self.send_lock.acquire()
            try:
                send_data = self.send_buffer.pop(0)
            finally:
                self.send_lock.release()
            
            self.uart_send(send_data)
            self.next_send_time = time.ticks_add(time.ticks_ms(), self.minimum_delay_between_sends)

    def uart_send(self, send_data: bytes):
        self.uart.write(send_data)

    def handle_rx(self):
        has_new_data = False
        if self.uart.any():
            new_data = self.uart.read()
            if new_data:
                self.current_line_buffer += new_data
                has_new_data = True
                self.current_buffer_deadline = time.ticks_add(time.ticks_ms(), self.receive_continue_timeout)
        
        if not has_new_data and len(self.current_line_buffer) > 0:
            if time.ticks_diff(self.current_buffer_deadline, time.ticks_ms()) < 0:
                self.receive_lock.acquire()
                try:
                    self.receive_buffer.append(self.current_line_buffer)
                    self.current_line_buffer = bytes()
                finally:
                    self.receive_lock.release()
    
    @staticmethod
    def make_from_config(comm_data: dict[str, str]) -> IJCI_UART:
        instance = int(comm_data.get('instance', 0))
        parity_raw = comm_data.get('parity', None)
        if parity_raw == 'None':
            parity = None
        elif parity_raw:
            parity = int(parity_raw)
        else:
            parity = None

        result = IJCI_UART(
            uart_channel = instance,
            tx_pin = int(comm_data.get('tx_pin', instance * 4)),
            rx_pin = int(comm_data.get('rx_pin', instance * 4 + 1)),
            baud = int(comm_data.get('baud', 115200)),
            bits = int(comm_data.get('bits', 8)),
            parity = parity,
            stop_bits = int(comm_data.get('stop_bits', 1))
            )
        
        result.receive_continue_timeout = int(comm_data.get('receive_continue_timeout', result.receive_continue_timeout))
        result.suspend_send_while_receiving = comm_data.get('suspend_send_while_receiving', str(result.suspend_send_while_receiving)) == 'True'
        result.minimum_delay_between_sends = int(comm_data.get('minimum_delay_between_sends', result.minimum_delay_between_sends))
        
        return result
        


class IJCI_UART_EN(IJCI_UART):
    def __init__(self, uart_channel: int, tx_pin: int, rx_pin: int, en_pin: int, write_en_state:bool=True, baud: int=115200,
                 bits: int=8, parity:int|None=None, stop_bits: int=1):
        super().__init__(uart_channel=uart_channel, tx_pin=tx_pin, rx_pin=rx_pin, baud=baud, bits=bits, parity=parity, stop_bits=stop_bits)
        self.en_pin = Pin(en_pin, Pin.OUT, value=not write_en_state)
        self.write_en_state = write_en_state
        self.friendly_name = 'UART With EN Pin'

    def uart_send(self, send_data: bytes):
        self.en_pin.value(self.write_en_state)
        super().uart_send(send_data)
        self.en_pin.value(not self.write_en_state)

    @staticmethod
    def make_from_config(comm_data: dict[str, str]) -> IJCI_UART_EN:
        instance = int(comm_data.get('instance', 0))
        parity_raw = comm_data.get('parity', None)
        if parity_raw == 'None':
            parity = None
        elif parity_raw:
            parity = int(parity_raw)
        else:
            parity = None

        result = IJCI_UART_EN(
            uart_channel = instance,
            tx_pin = int(comm_data.get('tx_pin', instance * 4)),
            rx_pin = int(comm_data.get('rx_pin', instance * 4 + 1)),
            en_pin = int(comm_data.get('en_pin', instance * 4 + 2)),
            write_en_state = comm_data.get('write_en_state', 'True') == 'True',
            baud = int(comm_data.get('baud', 115200)),
            bits = int(comm_data.get('bits', 8)),
            parity = parity,
            stop_bits = int(comm_data.get('stop_bits', 1))
            )
        
        result.receive_continue_timeout = int(comm_data.get('receive_continue_timeout', result.receive_continue_timeout))
        result.suspend_send_while_receiving = comm_data.get('suspend_send_while_receiving', str(result.suspend_send_while_receiving)) == 'True'
        result.minimum_delay_between_sends = int(comm_data.get('minimum_delay_between_sends', result.minimum_delay_between_sends))
        
        return result

class IJCI_UART_EN_Multi_Splitter(IJCI_UART):
    def __init__(self, uart_channel: int, tx_pin: int, rx_pin: int, en_dummy_pins: list[int] = [], write_en_state:bool=True, baud: int=115200,
                 bits: int=8, parity:int|None=None, stop_bits: int=1):
        super().__init__(uart_channel=uart_channel, tx_pin=tx_pin, rx_pin=rx_pin, baud=baud, bits=bits, parity=parity, stop_bits=stop_bits)
        self.write_en_state = write_en_state
        self.en_pins: list[Pin] = []
        self.friendly_name = 'UART With EN PIN Splitter'
        self.send_buffer_en = []
        self.current_en_pin = None

        for pin_id in en_dummy_pins:
            initial_state = write_en_state if (len(self.en_pins) == 0) else not write_en_state
            self.en_pins += [Pin(pin_id, Pin.OUT, value=initial_state)]

    def send(self, message: bytes):
        console().write('IJCI_UART_EN_Multi_Splitter.send() called directly', 'error')

    def send_en(self, message: bytes, en_pin: Pin):
        self.send_lock.acquire()
        try:
            self.send_buffer.append(message)
            self.send_buffer_en.append(en_pin)
        finally:
            self.send_lock.release()

    def uart_send(self, send_data: bytes):
        en_pin = self.send_buffer_en.pop(0)
        self.set_en_write_device(en_pin)
        super().uart_send(send_data)
        self.set_en_read_device(en_pin)

    def set_en_write_device(self, en_pin: Pin):
        for pin in self.en_pins:
            if pin != en_pin:
                pin.value(not self.write_en_state)
        en_pin.value(self.write_en_state)

    def set_en_read_device(self, en_pin: Pin):
        en_pin.value(not self.write_en_state)
        for pin in self.en_pins:
            if pin != en_pin:
                pin.value(self.write_en_state)

    def make_child(self, en_pin_raw: str, auto_set_read_device_after_send_raw: str = 'True') -> IJCI_UART_EN_Multi:
        en_pin = int(en_pin_raw)
        auto_set_read_device_after_send = (auto_set_read_device_after_send_raw == 'True')
        return IJCI_UART_EN_Multi(parent=self, en_pin=en_pin, auto_set_read_device_after_send=auto_set_read_device_after_send)
    
    @staticmethod
    def make_from_config(comm_data: dict[str, str]) -> IJCI_UART_EN_Multi_Splitter:
        instance = int(comm_data.get('instance', 0))
        parity_raw = comm_data.get('parity', None)
        if parity_raw == 'None':
            parity = None
        elif parity_raw:
            parity = int(parity_raw)
        else:
            parity = None

        en_pins_raw = comm_data.get('en_dummy_pins', '')
        if len(en_pins_raw) > 0:
            en_dummy_pins = [int(en_pin.strip()) for en_pin in en_pins_raw.split(',')]
        else:
            en_dummy_pins = []

        result = IJCI_UART_EN_Multi_Splitter(
            uart_channel = instance,
            tx_pin = int(comm_data.get('tx_pin', instance * 4)),
            rx_pin = int(comm_data.get('rx_pin', instance * 4 + 1)),
            en_dummy_pins = en_dummy_pins,
            write_en_state = comm_data.get('write_en_state', 'True') == 'True',
            baud = int(comm_data.get('baud', 115200)),
            bits = int(comm_data.get('bits', 8)),
            parity = parity,
            stop_bits = int(comm_data.get('stop_bits', 1))
            )
        
        result.receive_continue_timeout = int(comm_data.get('receive_continue_timeout', result.receive_continue_timeout))
        result.suspend_send_while_receiving = comm_data.get('suspend_send_while_receiving', str(result.suspend_send_while_receiving)) == 'True'
        result.minimum_delay_between_sends = int(comm_data.get('minimum_delay_between_sends', result.minimum_delay_between_sends))
        
        return result

class IJCI_UART_EN_Multi(IJCI_Base):
    def __init__(self, parent: IJCI_UART_EN_Multi_Splitter, en_pin: int, auto_set_read_device_after_send: bool = True):
        super().__init__()
        self.parent = parent
        initial_en_pin_state = parent.write_en_state if (len(parent.en_pins) == 0) else not parent.write_en_state
        self.en_pin = Pin(en_pin, Pin.OUT, value=initial_en_pin_state)
        self.auto_set_read_device_after_send = auto_set_read_device_after_send
        parent.en_pins += [self.en_pin]
        self.friendly_name = 'UART With EN Pin Split Client'
        self.internal_name = parent.internal_name + f'_en{en_pin}'

    def send(self, message: bytes):
        self.parent.send_en(message, self.en_pin)

    def check_receive(self) -> bool:
        return self.parent.check_receive()
    
    def receive(self) -> bytes:
        return self.parent.receive()

    @staticmethod
    def make_from_config(comm_data: dict[str, str]) -> IJCI_UART_EN_Multi_Splitter:
        return IJCI_UART_EN_Multi_Splitter.make_from_config(comm_data)
