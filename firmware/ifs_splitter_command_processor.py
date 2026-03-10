import ifs_splitter_system_consts as CONSTS
import ifs_splitter_user_consts as USER_CONSTS
import time

class IFSSplitterCommandProcessor:
    def __init__(self, serial, threadcomm, threadcomm_id, console_threadcomm_id):
        self.serial = serial
        self.threadcomm = threadcomm
        self.threadcomm_id = threadcomm_id
        self.console_threadcomm_id = console_threadcomm_id

        self.special_instructions = [
            name.replace("process_", "", 1)
            for name in dir(self)
            if name.startswith("process_") and callable(getattr(self, name))
        ]

        self.terminate = False
        self.is_running = False

        self.passthrough_target = USER_CONSTS.INITIAL_PASSTHROUGH_TARGET
        self.passthrough_z_command_enable_time = time.ticks_ms()

    def send(self, ifs_index, message, encode=True, linebreak=None, set_listen_ifs=True):
        prefix = "^^" if ifs_index < 0 else f"{ifs_index:02d}"
        if isinstance(message, str):
            self.threadcomm.send(self.console_threadcomm_id, f"{prefix}<< {message}")
        else:
            self.threadcomm.send(self.console_threadcomm_id, f"{prefix}<< 0x{message.hex()}")
        self.serial.send(ifs_index, message, encode, linebreak, set_listen_ifs)

    def execute(self):
        self.is_running = True
        while not self.terminate:
            input_data = None
            elements = None
            is_passthrough = self.passthrough_target >= 0

            if self.threadcomm.any(self.threadcomm_id):
                input_data = self.threadcomm.get(self.threadcomm_id)
                mod_input_data = input_data
                self.threadcomm.send(self.console_threadcomm_id, f"# >> {mod_input_data}")
                if is_passthrough:
                    if input_data.startswith("Z"):
                        elements = input_data.split()
                    else:
                        self.threadcomm.send(self.console_threadcomm_id, "# << Splitter unit is in passthrough mode. Commands from console other than Z commands are ignored.")
                        input_data = None
            elif self.serial.check_read_printer():
                input_data = self.serial.read_printer(not is_passthrough, not is_passthrough)
                if is_passthrough:
                    reset_z_command_delay = True
                    if time.ticks_diff(self.passthrough_z_command_enable_time, time.ticks_ms()) <= 0:
                        try:
                            input_decode = str(input_data, 'utf-8')
                            if input_decode.startswith("Z"):
                                elements = input_decode.split()
                                if elements[0] in self.special_instructions:
                                    input_data = input_decode
                                    reset_z_command_delay = False
                        except (UnicodeDecodeError, IndexError):
                            elements = None
                    if reset_z_command_delay:
                        self.passthrough_z_command_enable_time = time.ticks_add(time.ticks_ms(), CONSTS.PASSTHROUGH_MINIMUM_SILENCE_BEFORE_Z_COMMAND * 1000)
                    if isinstance(input_data, str):
                        mod_input_data = input_data.replace('\r', '\\r')
                        mod_input_data = mod_input_data.replace('\n', '\\n')
                    else:
                        mod_input_data = f"0x{input_data.hex()}"
                else:
                    mod_input_data = input_data
                self.threadcomm.send(self.console_threadcomm_id, f"^^>> {mod_input_data}")
            
            if input_data != None:
                if is_passthrough and elements == None:
                    self.send(self.serial.get_listen_ifs(), input_data, False, False)
                else:
                    if elements == None: # No point duplicating the effort
                        elements = input_data.split()
                    self.base_process(elements)

            if self.passthrough_target >= 0 and self.serial.check_read_ifs():
                input_data = self.serial.read_ifs(False, False)
                input_hex = input_data.hex()
                self.threadcomm.send(self.console_threadcomm_id, f"vv>> 0x{input_hex}")
                self.send(-1, input_data, False, False)

        self.is_running = False

    def base_process(self, elements):
        ifs_count = self.serial.get_ifs_count()            
        send_commands = [None] * ifs_count
        responses = [None] * ifs_count        

        instruction = elements[0]
        if instruction.startswith('Z') or instruction in self.special_instructions:
            target_cmd = f"process_{instruction}"
            if hasattr(self, target_cmd) and callable(getattr(self, target_cmd)):
                handler = getattr(self, target_cmd)
                handler(elements, send_commands, responses)
            else:
                responses[0] = f"{instruction} error. Unknown command"
            update_listen_ifs = len({cmd for cmd in send_commands if cmd}) == 1
        else: # Default - select based on C value if there is one, else send to last-used IFS
            target_ifs = self.serial.get_listen_ifs()
            for i in range(len(elements)):
                this_element = elements[i]
                if this_element.startswith('C'):
                    color_index = int(this_element[1:])
                    target_ifs = color_index // 4
                    elements[i] = "C" + str(color_index % 4)
                    break
            send_commands[target_ifs] = ' '.join(elements)
            self.serial.set_listen_ifs(target_ifs, True)
            update_listen_ifs = False
            
        command_count = 0
        response_count = 0
        for i in range(len(send_commands)):
            if send_commands[i] != None:
                command_count += 1
                self.send(i, send_commands[i], set_listen_ifs=update_listen_ifs)
                responses[i] = self.serial.read_ifs()
            if responses[i] != None:
                response_count += 1 # This may be set by a special handler or Z* command rather than the above branch, hence the seperate check        
        
        if command_count > 1:
            self.serial.set_listen_ifs()

        if response_count == 1:
            for r in responses:
                if r != None:
                    self.send(-1, r)
        elif response_count > 1:
            combined_response = '|'.join([f"IFS{i}:{responses[i]}" for i, r in enumerate(responses) if r])
            self.send(-1, combined_response)

    def send_all_merge_identical(self, command, responses):
        for i in range(len(responses)):
            self.send(i, command, set_listen_ifs=False)
            responses[i] = self.serial.read_ifs()
        unique_responses = {response for response in responses if response}
        if len(unique_responses) <= 1:
            for i in range(1, len(responses)):
                responses[i] = None
        self.serial.set_listen_ifs()

    def process_F12(self, elements, send_commands, responses):
        result = "F12 ok."
        for i in range(len(send_commands)):
            self.send(i, "F12", set_listen_ifs=False)
            this_response = self.serial.read_ifs()
            if this_response.startswith('F12 ok. '):
                result += this_response[7:-1]
            else:
                result += " 0 0 0 0"

        responses[0] = result + "\n"
        self.serial.set_listen_ifs()
                
    def process_F13(self, elements, send_commands, responses):
        # General state info - need to merge output
        # FFS_state: Magic numbers specifying status. Priority: (a) last-used IFS state if not 5; (b) any non-5 state; (c) 5; (d) None
        # silk_state: Bitwise value marking whether channels are loaded or not
        # chan: Currently active channel. 0 after reboot but not reset after F18
        # ffs_channels_insert: Bitwise value marking channels pending autoinsert (How to cancel?)
        # stall_state: Bitwise value marking channels with stall detected
        # unknown or not covered: report last used IFS's value [including jinsi_GCONF and qiehuan_GCONF], don't report if absent from last-used IFS
        result_state = CONSTS.IFS_FFS_STATE_OK
        result_silk = 0
        result_chan = 0
        result_channels_insert = 0
        result_stall_state = 0
        result_unknowns = {}
        listen_ifs = self.serial.get_listen_ifs()
        for i in range(len(send_commands)):
            self.send(i, "F13", set_listen_ifs=False)
            this_response = self.serial.read_ifs()
            if this_response.startswith('F13 ok. '):
                items = this_response[8:].split(' ')
                this_params = {}
                for i2 in range(len(items) // 2):
                    this_params[items[i2 * 2][:-1]] = items[i2 * 2 + 1]
                
                this_ffs_state = int(this_params.get('FFS_state', CONSTS.IFS_FFS_STATE_OK))
                if this_ffs_state != CONSTS.IFS_FFS_STATE_OK:
                    if result_state == CONSTS.IFS_FFS_STATE_OK or i == listen_ifs:
                        result_state = this_ffs_state
                
                this_silk_state = this_params.get('silk_state', 0)
                result_silk |= int(this_silk_state) << (i * 4)
                
                if i == listen_ifs:
                    this_chan = int(this_params.get('chan', 0))
                    if this_chan != 0:
                        result_chan = this_chan + (i * 4)
                        
                this_channels_insert = int(this_params.get('ffs_channels_insert', 0))
                result_channels_insert |= int(this_channels_insert) << (i * 4)
                
                this_stall_state = int(this_params.get('stall_state', 0))
                result_stall_state |= int(this_stall_state) << (i * 4)
                
                if i == listen_ifs:
                    for key, value in this_params.items():
                        if key not in ["FFS_state", "silk_state", "chan", "ffs_channels_insert", "stall_state"]:
                            result_unknowns[key] = value
                            
        result = f"F13 ok. FFS_state: {result_state} silk_state: {result_silk} chan: {result_chan} ffs_channels_insert: {result_channels_insert} stall_state: {result_stall_state}"
        for key, value in result_unknowns.items():
            result += f" {key}: {value}"
        
        responses[0] = result
        self.serial.set_listen_ifs()

    def process_F14(self, elements, send_commands, responses):
        # Stall detection info - need to merge output
        result = "F14 ok. stall:"
        for i in range(len(send_commands)):
            self.send(i, "F14", set_listen_ifs=False)
            this_response = self.serial.read_ifs()
            if this_response.startswith('F14 ok. stall: '):
                result += this_response[14:-1]
            else:
                result += " 0 0 0 0"
        responses[0] = result + ' '
        self.serial.set_listen_ifs()

    def process_F15(self, elements, send_commands, responses):
        self.send_all_merge_identical('F15', responses)

    def process_F18(self, elements, send_commands, responses):
        self.send_all_merge_identical('F18', responses)

    def process_F19(self, elements, send_commands, responses):
        for i in range(len(send_commands)):
            send_commands[i] = 'F19'

    def process_F21(self, elements, send_commands, responses):
        # Odometer info - need to merge output
        silk_data = ""
        stall_data = ""
        for i in range(len(send_commands)):
            self.send(i, "F21", set_listen_ifs=False)
            this_response = self.serial.read_ifs()
            if this_response.startswith("F21 ok. \r\n"):
                lines = this_response.split('\r\n')
                silk_data += lines[1][7:]
                stall_data += lines[2][8:]
            else:
                silk_data += "0 0 0 0 "
                stall_data += "0 0 0 0 "
        responses[0] = f"F21 ok. \r\n silk: {silk_data}\r\n stall: {stall_data}"
        self.serial.set_listen_ifs()

    def process_F22(self, elements, send_commands, responses):
        result_flag = 0
        for i in range(len(send_commands)):
            self.send(i, "F22", set_listen_ifs=False)
            this_response = self.serial.read_ifs()
            if this_response.startswith("F22 ok. "):
                result_flag += int(this_response[29:]) << (i * 4)
        responses[0] = f"F22 ok. ffs_channels_insert: {result_flag}"
        self.serial.set_listen_ifs()

    def process_F24(self, elements, send_commands, responses):
        # Clamp a channel - need to unclamp all other channels
        target_ifs = self.serial.get_listen_ifs()
        for i in range(len(elements)):
            this_element = elements[i]
            if this_element.startswith('C'):
                color_index = int(this_element[1:])
                target_ifs = (color_index - 1) // 4
                elements[i] = "C" + str(((color_index - 1) % 4) + 1)
                break
        for i in range(len(send_commands)):
            if i == target_ifs:
                send_commands[i] = ' '.join(elements)
            else:
                send_commands[i] = 'F18'
        self.serial.set_listen_ifs(target_ifs)
                
    def process_F37(self, elements, send_commands, responses):
        # Enter firmware update mode - not supported via splitter
        responses[0] = 'F37 error. Firmware update not supported in splitter mode. Recommended to connect directly to printer for update.'
        
    def process_F40(self, elements, send_commands, responses):
        # Stall counts - need to merge output
        result = "F40 ok.stall count: "
        for i in range(len(send_commands)):
            self.send(i, "F40", set_listen_ifs=False)
            this_response = self.serial.read_ifs()
            new_values = [0] * 4
            if this_response.startswith('F40 ok.stall count: '):
                response_elements = this_response[20:].split(' ')
                for i2 in range(4):
                    new_values[i2] = int(response_elements[i2 * 2 + 1])
            for i2 in range(4):
                result += f"C{(i * 4) + i2 + 1}: {new_values[i2]} "
        responses[0] = result
        self.serial.set_listen_ifs()
        
    def process_Z0(self, elements, send_commands, responses):
        ifs_index = -1
        for e in elements:
            if e.startswith('I'):
                ifs_index = int(e[1:])
        self.passthrough_target = ifs_index
        if ifs_index >= 0:
            responses[0] = f"Z0 ok. Passthrough mode to IFS {ifs_index} active"
        else:
            responses[0] = f"Z0 ok. Splitter mode active"
                
    def process_Z1(self, elements, send_commands, responses):
        unit_info = {}
        unit_info['script'] = CONSTS.SCRIPT_IDENTIFIER
        unit_info['author'] = CONSTS.SCRIPT_AUTHOR
        unit_info['version'] = CONSTS.SCRIPT_VERSION
        unit_info['hardware'] = CONSTS.SCRIPT_HARDWARE
        unit_info['supported_ifs_count'] = str(self.serial.get_ifs_count())
        unit_info['listen_ifs'] = str(self.serial.get_listen_ifs())
        responses[0] = 'Z1 ok. ' + ' '.join([f"{label}: \"{data}\"" for label, data in unit_info.items()])
        
    def process_Z2(self, elements, send_commands, responses):
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
                target_ifs = self.serial.get_listen_ifs()
                
            send_commands[target_ifs] = actual_command        
        except Exception as e:
            for i in range(len(send_commands)):
                send_commands[i] = None
                responses[i] = None
            responses[0] = f"Z1 error. Exception was raised, type {e.__class__.__name__}"

    def process_Z99(self, elements, send_commands, responses):
        self.terminate = True
        responses[0] = "Z99 ok. Terminating printer interaction thread"
