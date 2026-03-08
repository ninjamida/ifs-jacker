# Todo: Passthrough mode / activation
# Todo: How to clear insert flag?
# Todo: Logging to file (make sure to keep an eye on storage space!)

# Usage:
# - Connect printer and IFSes via MAX3485. I used this one: https://www.aliexpress.com/item/1005008338314594.html
#    - This code exploits an edge case with how UART and the MAX3485 board work. I cannot guarantee it will work
#      correctly on any other RS485 board, even other MAX3485-based ones.
#    - Note that the A/B wires on the IFS and printer are inverted compared to the MAX3485. So, connect the IFS's
#      line A to the MAX3485's line B and vice versa.
# - EN pins can be any spare GPIO pin.
# - Printer's MAX3485 needs a dedicated UART line and an EN pin.
# - All IFS's MAX3485s are wired in parallel to a single UART line, but each one has a dedicated EN pin.
# - To avoid doubt, each MAX3485 is wired to only a single IFS. The MAX3485's themselves are wired in parallel on
#   their TX / RX lines back to the RP2040.
# - Define pins / UART channels below.

# Porting to other boards:
# - This code uses multithreading, but only for providing console access to send commands. It should be easy to
#   strip that part out if porting to a single-core board; the core functionality does not use threads.
# - The connecting all IFSes to a single UART is a hack. I cannot guarantee it will work on other RS485 boards.

from machine import Pin, UART
import time
import _thread

# These variables are used for reporting status via Z1 only. They do not change the script's behavior in any way.
SCRIPT_IDENTIFIER = 'IFS Splitter'
SCRIPT_AUTHOR = 'ninjamida'
SCRIPT_VERSION = '0.01'
SCRIPT_HARDWARE = 'RP2040 Zero'
# End status variables

LOGGING = True
TIMESTAMP_DIGITS = 10
USE_FF_TERMINATOR = False # The printer generally follows up IFS commands with a 0xFF 0.2 seconds later. Set this
                          # to True to replicate this behavior. It isn't actually necessary in my experience.
ENABLE_CONSOLE = True # If true, a MicroPython debug console can be connected and commands send / read via it.
INITIAL_PASSTHROUGH_TARGET = 0  # Which IFS channel to initially be in passthrough mode to. Set to -1 to boot in
                                # splitter mode.

SPECIAL_HANDLING_INSTRUCTIONS = ['F12', 'F13', 'F14', 'F21', 'F22', 'F24', 'F37', 'F40']
SEND_ALL_INSTRUCTIONS = ['F15', 'F18', 'F19']

UART_BAUD = 115200
UART_BITS = 8
UART_PARITY = None
UART_STOP_BITS = 1

RECEIVE_START_TIMEOUT = 0.2
INTER_CHAR_TIMEOUT = 0.05
CONSOLE_RESPONSE_TIMEOUT = 1
CONSOLE_EXTRA_RESPONSE_TIMEOUT = 0.1

PRINTER_UART = 1
PRINTER_TX_PIN = 4
PRINTER_RX_PIN = 5
PRINTER_EN_PIN = 3

IFS_UART = 0
IFS_TX_PIN = 0
IFS_RX_PIN = 1
IFS_EN_PINS = [8, 9] # To add more IFSes, add their EN pin number to this line

IFS_FFS_STATE_OK = 5

uart_printer = None
en_pin_printer = None
uart_ifs = None
en_pins_ifs = []

last_ifs_used = 0

thread_comm_string = None
thread_comm_target = 0
thread_comm_lock = _thread.allocate_lock()
thread_comm_queued_command = None

passthrough_target = 0

def initialize():
    global uart_printer
    global en_pin_printer
    global uart_ifs
    global passthrough_target
    passthrough_target = INITIAL_PASSTHROUGH_TARGET
    uart_printer = UART(PRINTER_UART, baudrate=UART_BAUD, bits=UART_BITS, parity=UART_PARITY, stop=UART_STOP_BITS, tx=PRINTER_TX_PIN, rx=PRINTER_RX_PIN)
    en_pin_printer = Pin(PRINTER_EN_PIN, Pin.OUT, value=0)
    uart_ifs = UART(IFS_UART, baudrate=UART_BAUD, bits=UART_BITS, parity=UART_PARITY, stop=UART_STOP_BITS, tx=IFS_TX_PIN, rx=IFS_RX_PIN)
    for ifs_pin in IFS_EN_PINS:
        en_pins_ifs.append(Pin(ifs_pin, Pin.OUT, value=1))
    if passthrough_target >= 0:
        en_pins_ifs[passthrough_target].low()
    else:
        en_pins_ifs[0].low()

def append_to_thread_comm(text):
    global thread_comm_string
    if thread_comm_string == None:
        thread_comm_string = text
    else:
        thread_comm_string += "\r\n" + text
        
def save_incoming_command_from_console():
    global thread_comm_target
    global thread_comm_string
    global thread_comm_queued_command
    if thread_comm_target == 1 and thread_comm_string != None:
        thread_comm_queued_command = thread_comm_string
        thread_comm_string = None

def get_log_time():
    return f"{time.ticks_ms():0{TIMESTAMP_DIGITS}d}"

def log_out(ifs_index, message): # ifs_index == -1 for printer
    global thread_comm_target
    target_prefix = (str(ifs_index) + "<< ") if ifs_index >=0 else "^<< "
    if isinstance(message, str):
        log_msg = target_prefix + message
        log_msg = log_msg.replace('\r', '\\r')
        log_msg = log_msg.replace('\n', '\\n')
    else:
        log_msg = target_prefix + "{non text data}"
    thread_comm_lock.acquire()
    save_incoming_command_from_console()
    thread_comm_target = 0
    try:
        append_to_thread_comm(f"{get_log_time()} {log_msg}")
    finally:
        thread_comm_lock.release()

def log_in(ifs_index, message):
    global thread_comm_target
    source_prefix = "v>> " if ifs_index >= 0 else "^>> "
    if isinstance(message, str):
        log_msg = source_prefix + message
        log_msg = log_msg.replace('\r', '\\r')
        log_msg = log_msg.replace('\n', '\\n')
    else:
        log_msg = source_prefix + "{non text data}"
    thread_comm_lock.acquire()
    save_incoming_command_from_console()
    thread_comm_target = 0
    try:
        append_to_thread_comm(f"{get_log_time()} {log_msg}")
    finally:
        thread_comm_lock.release()

def send(ifs_index, message, encode=True, linebreak=None, terminator=None):
    global last_ifs_used
    log_out(ifs_index, message)
    if ifs_index >= 0:
        last_ifs_used = ifs_index
        if linebreak == None:
            linebreak = True
        if terminator == None:
            terminator = USE_FF_TERMINATOR
        en_pin = en_pins_ifs[ifs_index]
        unen_pins = [pin for pin in en_pins_ifs if pin != en_pin]
        uart = uart_ifs
    else:
        if linebreak == None:
            linebreak = False
        if terminator == None:
            terminator = False
        en_pin = en_pin_printer
        unen_pins = []
        uart = uart_printer    
    
    for pin in unen_pins:
        pin.low()
    en_pin.high()
    if linebreak:
        message += "\r\n"
    if encode:
        message = message.encode('utf-8')
    uart.write(message)
    uart.flush()
    if terminator:
        time.sleep(0.2)
        uart.write(b'\xff')
        uart.flush()
    en_pin.low()
    for pin in unen_pins:
        pin.high()
    
def read_ifs(decode=True, strip_linebreak=False):
    result = read(uart_ifs, decode, strip_linebreak)
    log_in(0, result)
    return result

def read_printer(decode=True, strip_linebreak=True):
    result = read(uart_printer, decode, strip_linebreak)
    log_in(-1, result)
    return result

def read(uart, decode, strip_linebreak):
    deadline = time.ticks_add(time.ticks_ms(), int(RECEIVE_START_TIMEOUT * 1000))
    result = bytes()
    while time.ticks_diff(deadline, time.ticks_ms()) > 0:
        if uart.any():
            result += uart.read()
            deadline = time.ticks_add(time.ticks_ms(), int(INTER_CHAR_TIMEOUT * 1000))
    
    if decode:
        try:
            result = str(result, 'utf-8')
            
            if strip_linebreak:
                if result.endswith('\n'):
                    result = result[:-2]
                if result.endswith('\r'):
                    result = result[:-2]
        except:
            result = "0x" + result.hex()
    
    return result
    
def check_read_ifs():
    return check_read(uart_ifs)

def check_read_printer():
    return check_read(uart_printer)

def check_read(uart):
    return uart.any()
        
def handle_printer_command():
    global thread_comm_queued_command
    global last_ifs_used
    if thread_comm_queued_command != None:
        command = thread_comm_queued_command
        thread_comm_queued_command = None
    elif check_read_printer():
        command = read_printer()
    else:
        command = None
    
    if command != None and len(command) > 0:
        elements = command.split(' ')
        
        send_commands = [None] * len(en_pins_ifs)
        responses = [None] * len(en_pins_ifs)
        # None = IFS wasn't queried
        # Empty string = No response received
        
        instruction = elements[0]
        if instruction.startswith('Z') or instruction in SPECIAL_HANDLING_INSTRUCTIONS: # F13, F24, Z*
            target_cmd = f"process_{instruction}"
            if target_cmd in globals():
                handler = globals()[target_cmd]
                handler(elements, send_commands, responses)
            else:
                if instruction in SPECIAL_HANDLING_INSTRUCTIONS:
                    responses[0] = f"Splitter error: {instruction} listed as special handling but no handler function is defined."
                else:
                    responses[0] = f"Splitter error: Unknown command {command}"
        elif instruction in SEND_ALL_INSTRUCTIONS: # F15, F18, F19
            for i in range(len(en_pins_ifs)):
                send_commands[i] = command
        else: # Default - select based on C value if there is one, else send to last-used IFS
            target_ifs = last_ifs_used
            for i in range(len(elements)):
                this_element = elements[i]
                if this_element.startswith('C'):
                    color_index = int(this_element[1:])
                    target_ifs = color_index // 4
                    elements[i] = "C" + str(color_index % 4)
                    break
            last_ifs_used = target_ifs
            send_commands[target_ifs] = ' '.join(elements)
            
        response_count = 0
        for i in range(len(send_commands)):
            if send_commands[i] != None:
                send(i, send_commands[i])
                responses[i] = read_ifs()
            if responses[i] != None:
                response_count += 1 # This may be set by a special handler or Z* command rather than the above branch, hence the seperate check
                
        if response_count == 1:
            for r in responses:
                if r != None:
                    send(-1, r)
        elif response_count > 1:
            combined_response = '|'.join([f"IFS{i}:{responses[i]}" for i, r in enumerate(responses) if r is not None])
            send(-1, combined_response)
            
# Special handling:
# SPECIAL_HANDLING_INSTRUCTIONS = ['F12', 'F13', 'F14', 'F21', 'F22', 'F24', 'F37', 'F40']

def process_F12(elements, send_commands, responses):
    result = "F12 ok."
    for i in range(len(send_commands)):
        send(i, "F12")
        this_response = read_ifs()
        if this_response.startswith('F12 ok. '):
            result += this_response[7:-1]
        else:
            result += " 0 0 0 0"
    responses[0] = result + "\n"
    pass
            
def process_F13(elements, send_commands, responses):
    # General state info - need to merge output
    # FFS_state: Magic numbers specifying status. Priority: (a) last-used IFS state if not 5; (b) any non-5 state; (c) 5; (d) None
    # silk_state: Bitwise value marking whether channels are loaded or not
    # chan: Currently active channel. 0 after reboot but not reset after F18
    # ffs_channels_insert: Bitwise value marking channels pending autoinsert (How to cancel?)
    # stall_state: Bitwise value marking channels with stall detected
    # unknown or not covered: report last used IFS's value [including jinsi_GCONF and qiehuan_GCONF], don't report if absent from last-used IFS
    result_state = IFS_FFS_STATE_OK
    result_silk = 0
    result_chan = 0
    result_channels_insert = 0
    result_stall_state = 0
    result_unknowns = {}
    for i in range(len(send_commands)):
        send(i, "F13")
        this_response = read_ifs()
        if this_response.startswith('F13 ok. '):
            items = this_response[8:].split(' ')
            this_params = {}
            for i2 in range(len(items) / 2):
                this_params[items[i2 * 2][:-1]] = items[i2 * 2 + 1]
            
            this_ffs_state = int(this_params.get('FFS_state', IFS_FFS_STATE_OK))
            if this_ffs_state != IFS_FFS_STATE_OK:
                if result_state == IFS_FFS_STATE_OK or i == last_ifs_used:
                    result_state = this_ffs_state
            
            this_silk_state = this_params.get('silk_state', 0)
            result_silk |= int(this_silk_state) << (i * 4)
            
            if i == last_ifs_used:
                this_chan = int(this_params.get('chan', 0))
                if this_chan != 0:
                    result_chan = this_chan + (i * 4)
                    
            this_channels_insert = int(this_params.get('ffs_channels_insert', 0))
            result_channels_insert |= int(this_channels_insert) << (i * 4)
            
            this_stall_state = int(this_params.get('stall_state', 0))
            result_stall_state |= int(this_stall_state) << (i * 4)
            
            if i == last_ifs_used:
                for key, value in this_params.items():
                    if key not in ["FFS_state", "silk_state", "chan", "ffs_channels_insert", "stall_state"]:
                        result_unknowns[key] = value
                        
    result = f"F13 ok. FFS_state: {result_state} silk_state: {result_silk} chan: {result_chan} ffs_channels_insert: {result_channels_insert} stall_state: {result_stall_state}"
    for key, value in result_unknowns.items():
        result += f" {key}: {value}"
    
    responses[0] = result

def process_F14(elements, send_commands, responses):
    # Stall detection info - need to merge output
    result = "F14 ok. stall:"
    for i in range(len(send_commands)):
        send(i, "F14")
        this_response = read_ifs()
        if this_response.startswith('F14 ok. stall: '):
            result += this_response[14:-1]
        else:
            result += " 0 0 0 0"
    responses[0] = result + ' '
    pass

def process_F21(elements, send_commands, responses):
    # Odometer info - need to merge output
    silk_data = ""
    stall_data = ""
    for i in range(len(send_commands)):
        send(i, "F21")
        this_response = read_ifs()
        if this_response.startswith("F21 ok. \r\n"):
            lines = this_response.split('\r\n')
            silk_data += lines[1][7:]
            stall_data += lines[2][8:]
        else:
            silk_data += "0 0 0 0 "
            stall_data += "0 0 0 0 "
    responses[0] = f"F21 ok. \r\n silk: {silk_data}\r\n stall: {stall_data}"

def process_F22(elements, send_commands, responses):
    result_flag = 0
    for i in range(len(send_commands)):
        send(i, "F22")
        this_response = read_ifs()
        if this_response.startswith("F22 ok. "):
            result_flag += int(this_response[29:]) << (i * 4)
    responses[0] = f"F22 ok. ffs_channels_insert: {result_flag}"

def process_F24(elements, send_commands, responses):
    # Clamp a channel - need to unclamp all other channels
    global last_ifs_used
    target_ifs = last_ifs_used
    for i in range(len(elements)):
        this_element = elements[i]
        if this_element.startswith('C'):
            color_index = int(this_element[1:])
            target_ifs = color_index // 4
            elements[i] = "C" + str(color_index % 4)
            break
    last_ifs_used = target_ifs
    for i in range(len(send_commands)):
        if i == target_ifs:
            send_commands[i] = ' '.join(elements)
        else:
            send_commands[i] = 'F18'
            
def process_F37(elements, send_commands, responses):
    # Enter firmware update mode - not currently supported via splitter
    responses[0] = 'F37 error. Firmware update not supported in splitter mode. Use passthrough mode or connect directly to printer.'
    
def process_F40(elements, send_commands, responses):
    # Stall counts - need to merge output
    result = "F40 ok.stall count: "
    for i in range(len(send_commands)):
        send(i, "F40")
        this_response = read_ifs()
        new_values = [0] * 4
        if this_response.startswith('F40 ok.stall count: '):
            response_elements = this_response[20:].split(' ')
            for i2 in range(4):
                new_values[i2] = int(response_elements[i2 * 2 + 1])
        for i2 in range(4):
            result += f"C{(i * 4) + i2 + 1}: {new_values[i2]} "
    responses[0] = result
    
def process_Z0(elements, send_commands, responses):
    global passthrough_target
    ifs_index = -1
    for e in elements:
        if e.startswith('I'):
            ifs_index = int(e[1:])
    passthrough_target = ifs_index
    if ifs_index >= 0:
        responses[0] = f"Z0 ok. Passthrough mode to IFS {ifs_index} active"
    else:
        responses[0] = f"Z0 ok. Splitter mode active"
            
def process_Z1(elements, send_commands, responses):
    unit_info = {}
    unit_info['script'] = SCRIPT_IDENTIFIER
    unit_info['author'] = SCRIPT_AUTHOR
    unit_info['version'] = SCRIPT_VERSION
    unit_info['hardware'] = SCRIPT_HARDWARE
    unit_info['supported_ifs_count'] = str(len(en_pins_ifs))
    unit_info['last_ifs_used'] = str(last_ifs_used)
    responses[0] = 'Z1 ok. ' + ' '.join([f"{label}: \"{data}\"" for label, data in unit_info.items()])
    
def process_Z2(elements, send_commands, responses):
    if len(elements) < 2:
        responses[0] = 'Z1 error. No params provided'
        return
    try:
        target_ifs = -1
        if elements[1].startswith('I'):
            target_ifs = int(elements[1][1:])
            actual_command = ' '.join(elements[2:])
        else:
            actual_command = ' '.join(elements[1:])
            
        if target_ifs == -1:
            target_ifs = last_ifs_used
            
        send_commands[target_ifs] = actual_command        
    except Exception as e:
        for i in range(len(send_commands)):
            send_commands[i] = None
            responses[i] = None
        responses[0] = f"Z1 error. Exception was raised, type {e.__class__.__name__}"

def update_loop():
    # Runs on second core
    global passthrough_target
    global thread_comm_queued_command
    while True:
        if ENABLE_CONSOLE:
            thread_comm_lock.acquire()
            try:
                save_incoming_command_from_console()
            finally:
                thread_comm_lock.release()
            if thread_comm_queued_command == "Z0 I-1":
                passthrough_target = -1
        
        if passthrough_target >= 0:
            if check_read_ifs():
                in_data = read_ifs(False, False)
                send(-1, in_data, False)
            
            if check_read_printer():
                in_data = read_printer(False, False)
                try:
                    decoded_data = str(in_data, 'utf-8')
                    if decoded_data == "Z0 I-1":
                        passthrough_target = -1
                        thread_comm_queued_command = decoded_data
                except:
                    pass
                
                if passthrough_target >= 0:
                    send(passthrough_target, in_data, False)
                
        if passthrough_target < 0:
            handle_printer_command()

def main():
    global thread_comm_string
    global thread_comm_target
    print(get_log_time() + " Starting up")
    initialize()
    print(get_log_time() + " Starting second thread")
    _thread.start_new_thread(update_loop, ())
    response_expected = 0
    print(get_log_time() + " Beginning main thread loop")
    while True:
        if response_expected > 0:
            delay = CONSOLE_RESPONSE_TIMEOUT if response_expected == 1 else CONSOLE_EXTRA_RESPONSE_TIMEOUT
            deadline = time.ticks_add(time.ticks_ms(), int(CONSOLE_RESPONSE_TIMEOUT * 1000))
            while time.ticks_diff(deadline, time.ticks_ms()) > 0:
                if thread_comm_target == 0 and thread_comm_string != None:
                    response_expected = 0
                    break
                time.sleep(0.01)
            if response_expected == 1:
                print(get_log_time() + " ### No response received")
                if passthrough_target >= 0:
                    print(get_log_time() + " ### Splitter is in passthrough mode; enter Z0 I-1 to enter splitter mode")
            response_expected = 0
        
        if thread_comm_target == 0 and thread_comm_string != None:
            thread_comm_lock.acquire()
            try:
                print(thread_comm_string)
                thread_comm_string = None
            finally:
                thread_comm_lock.release()
            response_expected = 2
            continue
        
        if ENABLE_CONSOLE:
            console_input = input((" " * TIMESTAMP_DIGITS) + " ### Enter command: ")
            thread_comm_lock.acquire()
            try:
                if thread_comm_target == 0 and thread_comm_string != None:
                    print(get_log_time() + " ### Message was pending before command:")
                    print(thread_comm_string)
                    thread_comm_string = None
                if len(console_input) > 0:
                    thread_comm_string = console_input
                    thread_comm_target = 1
            finally:
                thread_comm_lock.release()
            
            if len(console_input) > 0:
                response_expected = 1
                deadline = time.ticks_add(time.ticks_ms(), CONSOLE_RESPONSE_TIMEOUT * 1000)
                while time.ticks_diff(deadline, time.ticks_ms()) > 0:
                    if thread_comm_string != None:
                        break
            else:
                response_expected = 0
        else:
            time.sleep(0.01)
main()
