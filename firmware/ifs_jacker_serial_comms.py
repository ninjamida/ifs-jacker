from machine import UART, Pin
import time
import ifs_jacker_system_consts as CONSTS

class IFSJackerSerialComms:
    def __init__(self, config):
        self.config = config
        self.en_pins_ifs = []

        self.listen_ifs = 0

        self.uart_printer = UART(self.config.printer_uart, baudrate=CONSTS.UART_BAUD, bits=CONSTS.UART_BITS,
                            parity=CONSTS.UART_PARITY, stop=CONSTS.UART_STOP_BITS, tx=self.config.printer_tx_pin,
                            rx=self.config.printer_rx_pin)
        self.en_pin_printer = Pin(self.config.printer_en_pin, Pin.OUT, value=0)
        self.uart_ifs = UART(self.config.ifs_uart, baudrate=CONSTS.UART_BAUD, bits=CONSTS.UART_BITS, parity=CONSTS.UART_PARITY,
                        stop=CONSTS.UART_STOP_BITS, tx=self.config.ifs_tx_pin, rx=self.config.ifs_rx_pin)
        
        first = True
        for ifs_pin in self.config.ifs_en_pins:
            self.en_pins_ifs.append(Pin(ifs_pin, Pin.OUT, value=0 if first else 1))
            first = False

    def send(self, ifs_index, message, encode=True, linebreak=None, set_listen_ifs=True):
        if ifs_index >= 0:
            if set_listen_ifs:
                self.listen_ifs = ifs_index
            if linebreak == None:
                linebreak = True
            en_pin = self.en_pins_ifs[ifs_index]
            unen_pins = [pin for pin in self.en_pins_ifs if pin != en_pin]
            uart = self.uart_ifs
        else:
            if linebreak == None:
                linebreak = False
            en_pin = self.en_pin_printer
            unen_pins = []
            uart = self.uart_printer    
        
        for pin in unen_pins:
            pin.low()
        en_pin.high()
        if linebreak:
            message += "\r\n"
        if encode:
            message = message.encode('utf-8')
        uart.write(message)
        uart.flush()
        en_pin.low()
        for pin in unen_pins:
            pin.high()
        
    def read_ifs(self, decode=True, strip_linebreak=False):
        result = self.read(self.uart_ifs, decode, strip_linebreak)
        return result

    def read_printer(self, decode=True, strip_linebreak=True):
        result = self.read(self.uart_printer, decode, strip_linebreak)
        return result

    def read(self, uart, decode, strip_linebreak):
        deadline = time.ticks_add(time.ticks_ms(), int(CONSTS.RECEIVE_START_TIMEOUT * 1000))
        result = bytes()
        while time.ticks_diff(deadline, time.ticks_ms()) > 0:
            if uart.any():
                result += uart.read()
                deadline = time.ticks_add(time.ticks_ms(), int(CONSTS.INTER_CHAR_TIMEOUT * 1000))
        
        if decode:
            try:
                out_result = str(result, 'utf-8')
                
                if strip_linebreak:
                    if out_result.endswith('\n'):
                        out_result = out_result[:-2]
                    if out_result.endswith('\r'):
                        out_result = out_result[:-2]
            except:
                out_result = "0x" + result.hex()
        else:
            out_result = result
        
        return out_result
        
    def check_read_ifs(self):
        return self.check_read(self.uart_ifs)

    def check_read_printer(self):
        return self.check_read(self.uart_printer)

    def check_read(self, uart):
        return uart.any()
    
    def get_ifs_count(self):
        return len(self.en_pins_ifs)
    
    def get_listen_ifs(self):
        return self.listen_ifs
    
    def set_listen_ifs(self, ifs_index=-1, flag_only=False): # Call with ifs_index = -1 to reset the EN pins without changing the target IFS
        if ifs_index >= 0:
            self.listen_ifs = ifs_index
        if not flag_only:
            self.en_pins_ifs[self.listen_ifs].low()
            for i, pin in enumerate(self.en_pins_ifs):
                if i != self.listen_ifs:
                    pin.high()
