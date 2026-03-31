from machine import UART, Pin
import time

class IJCI_Base:
    def __init__(self):
        pass

    def send(self, message: bytes):
        pass

    def check_receive(self) -> bool:
        return False
    
    def receive(self) -> bytes:
        return bytes()
    
class IJCI_UART(IJCI_Base):
    def __init__(self, uart_channel: int, tx_pin: int, rx_pin: int, baud:int=115200, bits:int=8, parity:int|None=None, stop_bits:int=1):
        super().__init__()
        self.uart = UART(
            uart_channel, baudrate=baud, bits=bits, parity=parity, stop=stop_bits,
            tx=tx_pin, rx=rx_pin
            )
        self.receive_start_timeout = int(0.2 * 1000)
        self.receive_continue_timeout = int(0.05 * 1000)
        
    def send(self, message: bytes):
        self.uart.write(message)
        self.uart.flush()

    def check_receive(self) -> bool:
        return self.uart.any() > 0
    
    def receive(self) -> bytes:
        deadline = time.ticks_add(time.ticks_ms(), self.receive_start_timeout)
        result = bytes()
        while time.ticks_diff(deadline, time.ticks_ms()) > 0:
            if self.uart.any():
                get_data = self.uart.read()
                if get_data != None:
                    result += get_data
                    deadline = time.ticks_add(time.ticks_ms(), self.receive_continue_timeout)
        return result

class IJCI_UART_EN(IJCI_UART):
    def __init__(self, uart_channel: int, tx_pin: int, rx_pin: int, en_pin: int, write_en_state:bool=True, baud: int=115200,
                 bits: int=8, parity:int|None=None, stop_bits: int=1):
        super().__init__(uart_channel=uart_channel, tx_pin=tx_pin, rx_pin=rx_pin, baud=baud, bits=bits, parity=parity, stop_bits=stop_bits)
        self.en_pin = Pin(en_pin, Pin.OUT, value=not write_en_state)
        self.write_en_state = write_en_state

    def send(self, message: bytes):
        self.en_pin.value(self.write_en_state)
        super().send(message)
        self.en_pin.value(not self.write_en_state)

class IJCI_UART_EN_Multi_Splitter(IJCI_UART):
    def __init__(self, uart_channel: int, tx_pin: int, rx_pin: int, write_en_state:bool=True, baud: int=115200,
                 bits: int=8, parity:int|None=None, stop_bits: int=1):
        super().__init__(uart_channel=uart_channel, tx_pin=tx_pin, rx_pin=rx_pin, baud=baud, bits=bits, parity=parity, stop_bits=stop_bits)
        self.write_en_state = write_en_state
        self.en_pins = []

    def set_write_device(self, en_pin: Pin):
        for pin in self.en_pins:
            if pin != en_pin:
                pin.value(not self.write_en_state)
        en_pin.value(self.write_en_state)

    def set_read_device(self, en_pin: Pin):
        en_pin.value(not self.write_en_state)
        for pin in self.en_pins:
            if pin != en_pin:
                pin.value(self.write_en_state)

    def make_device_interface(self, en_pin: int, auto_set_read_device_after_send: bool = True) -> IJCI_UART_EN_Multi:
        return IJCI_UART_EN_Multi(parent_multi=self, en_pin=en_pin, auto_set_read_device_after_send=auto_set_read_device_after_send)

class IJCI_UART_EN_Multi(IJCI_Base):
    def __init__(self, parent_multi: IJCI_UART_EN_Multi_Splitter, en_pin: int, auto_set_read_device_after_send: bool = True):
        self.parent = parent_multi
        initial_en_pin_state = parent_multi.write_en_state if (len(parent_multi.en_pins) == 0) else not parent_multi.write_en_state
        self.en_pin = Pin(en_pin, Pin.OUT, value=initial_en_pin_state)
        self.auto_set_read_device_after_send = auto_set_read_device_after_send
        parent_multi.en_pins += [self.en_pin]

    def send(self, message: bytes):
        self.parent.set_write_device(self.en_pin)
        self.parent.send(message)
        if self.auto_set_read_device_after_send:
            self.parent.set_read_device(self.en_pin)

    def check_receive(self) -> bool:
        return self.parent.check_receive()
    
    def receive(self) -> bytes:
        return self.parent.receive()
    
    def set_as_write_device(self):
        self.parent.set_write_device(self.en_pin)

    def set_as_read_device(self):
        self.parent.set_read_device(self.en_pin)
