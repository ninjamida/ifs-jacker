import _thread, re, time
from comm import _IJ_Comm_Abstract, IJ_Comm_Manager
from peripheral import IJ_Peripheral, load_peripheral
from console import get_console
from util import SCRIPT_IDENTIFIER, SCRIPT_VERSION, SCRIPT_AUTHOR

QCR_DISCARD = 0  # Response from MMU will be ignored
QCR_INTERNAL = 1 # Response from MMU will be processed internally but not passed to the printer (no action on timeout)
QCR_FORWARD = 2  # Response from MMU will be forwarded to the printer (no action on timeout)
QCR_F13 = 3      # Special handling for F13
QCR_SILENT = 4   # Same as QCR_INTERNAL but hides from console (unless "silent" type is specifically revealed)

class QueuedCommand:
    def __init__(self, target_mmu_id: int, response_handling: int, command: str):
        self.target_mmu_id = target_mmu_id
        self.response_handling = response_handling
        self.command = command

class IJ_Core:
    terminate = False

    def __init__(self):
        self.console = get_console()

        self.started = False
        self.terminate = False
        self.finished = False

        self.comm: IJ_Comm_Manager = None # type: ignore

        self.printer_comm: _IJ_Comm_Abstract | None = None
        self.mmu_comms: list[_IJ_Comm_Abstract] = []

        self.ffs_state = 3
        self.silk_state = 0
        self.chan = 0
        self.channels_insert = 0
        self.stall_state = 0

        self.active_mmu_id = 0
        self.status_mmu_index = 0
        self.cmd_queue: list[QueuedCommand] = []
        self.send_queue_this_iteration = False

        self.sent_target_mmu = 0
        self.sent_response_handling = QCR_DISCARD
        self.sent_timeout: int | None = None

        self.printer_connected_timeout_expire = None

        self.mmu_timeouts = 0
        self.mmu_requests = 0

        self.peripherals: list[IJ_Peripheral] = []

        self.force_present_mask = 0
        self.force_absent_mask = ~0

        self.printer_connected_timeout = 3 * 1000

        self.mmu_response_timeout = int(0.05 * 1000)

        self.include_channel_count_in_status = True
        self.include_peripherals_in_status = True

    def start_thread(self):
        _thread.start_new_thread(self.run, ())

    def send_printer(self, data: str):
        if self.printer_comm:
            self.printer_comm.send(data)
        self.console.print(f'printer << {data}', 'data')

    def update_printer(self):
        printer_incoming_data = self.console.get_input()
        if not printer_incoming_data:
            if self.printer_comm and self.printer_comm.check_receive():
                printer_incoming_data = self.printer_comm.receive().strip()
                if len(printer_incoming_data) > 0:
                    self.console.print(f'printer >> {printer_incoming_data}', 'data')
            else:
                printer_incoming_data = ''

        if len(printer_incoming_data) > 0:
            if self.printer_connected_timeout > 0:
                if self.printer_connected_timeout_expire is None:
                    self.console.print('Printer connected', 'info')
                    for peripheral in self.peripherals:
                        if peripheral.use_primary_thread and peripheral.auto_thread_lock:
                            peripheral.thread_lock.acquire()
                        try:
                            peripheral.activate()
                        finally:
                            if peripheral.use_primary_thread and peripheral.auto_thread_lock:
                                peripheral.thread_lock.release()
                self.printer_connected_timeout_expire = time.ticks_add(time.ticks_ms(), self.printer_connected_timeout)

            if printer_incoming_data == 'F13\r\nF13\r\n': # Z-Mod and native screen are fighting
                printer_incoming_data = 'F13' # We can't control who receives it, but we can make sure we just send a normal F13 response back
            in_split = printer_incoming_data.split(' ')
            f = 0
            c = 0
            s = 0
            l = 0
            z = 0
            mmu = self.active_mmu_id
            for element in in_split:
                if len(element) > 1:
                    try:
                        param = element[0]
                        if param == 'F': f = int(element[1:])
                        if param == 'C': c = int(element[1:])
                        if param == 'S': s = int(element[1:])
                        if param == 'L': l = int(element[1:])
                        if param == 'Z': z = int(element[1:])
                    except:
                        pass

            if z > 0:
                self.handle_z_command(f, c, l, s, z, in_split)

            if z == 0 and f > 0:
                self.hide_next_response = False
                cmd_inserted = False

                if c > 0:
                    mmu = (c - 1) // 4
                    c = ((c - 1) % 4) + 1
                    self.active_mmu_id = mmu
                    self.status_mmu_index = mmu
                if f == 18 or f == 24:
                    for i in reversed(range(len(self.mmu_comms))):
                        if i != self.active_mmu_id:
                            self.cmd_queue.insert(0, QueuedCommand(i, QCR_DISCARD, 'F18\r\n'))
                if f == 37:
                    # Not safe to do firmware updates through IFS Jacker at this time. Block it entirely by substituting it to F13.
                    f = 13
                if f == 13:
                    self.cmd_queue.insert(0, QueuedCommand(self.active_mmu_id, QCR_F13, 'F13\r\n'))
                    self.send_queue_this_iteration = True
                    cmd_inserted = True

                if not cmd_inserted:
                    elements = [f'F{f}']
                    if c > 0:
                        elements.append(f'C{c}')
                        if s > 0 and l > 0:
                            elements.append(f'L{l} S{s}')
                    elements.append('\r\n')
                    self.cmd_queue.insert(0, QueuedCommand(self.active_mmu_id, QCR_FORWARD, ' '.join(elements)))
                    self.send_queue_this_iteration = True

    def handle_z_command(self, f: int, c: int, l: int, s: int, z: int, in_split: list[str]):
        if z == 1:
            self.send_printer('Z1 ok.')

        if z == 2:
            data = ['Z2 ok.']
            data += [f'software: "{SCRIPT_IDENTIFIER}"']
            data += [f'version: "{SCRIPT_VERSION}"']
            data += [f'author: "{SCRIPT_AUTHOR}"']
            data += [f'mmu_count: {len(self.mmu_comms)}']
            data += [f'channel_count: {len(self.mmu_comms) * 4}']
            data += [f'peripheral_count: {len(self.peripherals)}']
            data += [f'mmu_requests: {self.mmu_requests}']
            data += [f'mmu_timeouts: {self.mmu_timeouts}']
            self.send_printer(' '.join(data))

        if z == 3:
            data = ['Z3 ok.']
            for i, peripheral in enumerate(self.peripherals):
                data += [f'peripheral_{i}: "{peripheral.identifier}"']
            self.send_printer(' '.join(data))

        if z == 4:
            data = ['Z4 ok.']
            for i, peripheral in enumerate(self.peripherals):
                if peripheral.report_in_Z4 or f != 0:
                    data += [peripheral.get_status_info()]
            self.send_printer(' '.join(data))

        if z == 5:
            if c >= 0 and c < len(self.peripherals):
                peripheral = self.peripherals[c]
                if peripheral.use_primary_thread and peripheral.auto_thread_lock:
                    peripheral.thread_lock.acquire()
                try:
                    result = self.peripherals[c].handle_command(f, l, s, in_split)
                    self.send_printer(f'Z5 ok. {result}')
                finally:
                    if peripheral.use_primary_thread and peripheral.auto_thread_lock:
                        peripheral.thread_lock.release()
            else:
                self.send_printer(f'Z5 ok. Invalid peripheral index {c}')

        if z == 6:
            config = {}
            for item in in_split[1:]:
                pair = item.split('=', 1)
                if len(pair) == 2:
                    config[pair[0]] = pair[1]
            try:
                new_index = len(self.peripherals)
                new_peripheral = load_peripheral(new_index, config, self.comm.comm_list)
                self.peripherals.append(new_peripheral)
                self.comm.add_peripheral(new_peripheral)
                self.send_printer(f'Z6 ok. Peripheral {new_index} added')
            except:
                self.send_printer('Z6 ok. Failed')


        if z == 99:
            self.terminate = True
            self.send_printer('Z99 ok. Terminating')

    def send_mmu(self, data: str, mmu: int):
        self.mmu_requests += 1
        if len(self.mmu_comms) > 0:
            self.mmu_comms[mmu].send(data)
            if self.sent_response_handling != QCR_SILENT:
                self.console.print(f'mmu{mmu} << {data}', 'data')

    def update_mmu(self):
        if len(self.mmu_comms) == 0:
            return
        
        if self.printer_connected_timeout_expire is None and self.printer_connected_timeout > 0:
            return

        if self.sent_timeout:
            mmu = self.mmu_comms[self.sent_target_mmu]
            if mmu.check_receive():
                mmu_incoming_data = mmu.receive().strip()
                if self.sent_response_handling != QCR_SILENT:
                    self.console.print(f'mmu{self.sent_target_mmu} >> {mmu_incoming_data}', 'data')
                if len(mmu_incoming_data) > 0:
                    self.sent_timeout = None

                    if self.sent_response_handling != QCR_DISCARD:
                        cmd_id = int(mmu_incoming_data.split(' ', 1)[0][1:])

                        if cmd_id == 13:
                            self.update_cached_F13_data(mmu_incoming_data, self.sent_target_mmu)
                            if self.sent_response_handling == QCR_FORWARD:
                                self.sent_response_handling = QCR_F13

                        if self.sent_response_handling == QCR_FORWARD:
                            mmu_incoming_data = re.sub(
                                r'(channel|chan) (\d+)',
                                lambda c: f'{c.group(1)} {int(c.group(2)) + (self.sent_target_mmu * 4)}',
                                mmu_incoming_data
                            )
                            self.send_printer(mmu_incoming_data)

            if self.sent_timeout and time.ticks_diff(self.sent_timeout, time.ticks_ms()) < 0:
                self.sent_timeout = None
                self.mmu_timeouts += 1
                if self.sent_response_handling == QCR_F13:
                    self.update_cached_F13_data('', self.sent_target_mmu)

            if not self.sent_timeout and self.sent_response_handling == QCR_F13: # "if not self.sent_timeout" at this point means either (a) we got a response or (b) we've timed out
                self.send_F13_response()

        if not self.sent_timeout:
            if len(self.cmd_queue) > 0 and self.send_queue_this_iteration:
                next_cmd = self.cmd_queue.pop(0)
            else:
                next_cmd = QueuedCommand(self.status_mmu_index, QCR_SILENT, 'F13\r\n')
                self.status_mmu_index = (self.status_mmu_index + 1) % len(self.mmu_comms)

            self.send_queue_this_iteration = not self.send_queue_this_iteration

            self.sent_target_mmu = next_cmd.target_mmu_id
            self.sent_response_handling = next_cmd.response_handling
            self.sent_timeout = time.ticks_add(time.ticks_ms(), self.mmu_response_timeout)

            self.send_mmu(next_cmd.command, next_cmd.target_mmu_id)

    def update_cached_F13_data(self, new_F13_response: str, source_mmu: int):
        cmd_split = new_F13_response.split(' ')

        new_ffs_state = 5
        new_silk_state = 0
        new_chan = 0
        new_channels_insert = 0
        new_stall_state = 0

        for i in range(2, len(cmd_split), 2):
            if i + 1 < len(cmd_split):
                key = cmd_split[i]
                value = cmd_split[i + 1]
                if key == 'FFS_state:': new_ffs_state = int(value)
                if key == 'silk_state:': new_silk_state = int(value)
                if key == 'chan:': new_chan = int(value)
                if key == 'ffs_channels_insert:': new_channels_insert = int(value)
                if key == 'stall_state:': new_stall_state = int(value)

        shift = source_mmu * 4
        mask = ~(0b1111 << shift)
        self.silk_state = (self.silk_state & mask) | (new_silk_state << shift)
        self.channels_insert = (self.channels_insert & mask) | (new_channels_insert << shift)
        self.stall_state = (self.stall_state & mask) | (new_stall_state << shift)

        if source_mmu == self.active_mmu_id:
            self.chan = new_chan + source_mmu * 4
            if new_ffs_state in [7, 11, 12, 15, 18, 22, 23, 26, 29, 33, 34, 37, 40, 44, 45, 48]:
                self.ffs_state = new_ffs_state + (source_mmu * 44) # 11 per channel
            else:
                self.ffs_state = new_ffs_state

        self.silk_state &= self.force_absent_mask
        self.silk_state |= self.force_present_mask

    def send_F13_response(self):
        out_text = [f'F13 ok. FFS_state: {self.ffs_state} silk_state: {self.silk_state} chan: {self.chan}']
        out_text += [f'ffs_channels_insert: {self.channels_insert} stall_state: {self.stall_state}']

        if self.include_channel_count_in_status:
            out_text += [f'channel_count: {len(self.mmu_comms) * 4}']

        if self.include_peripherals_in_status:
            for i, peripheral in enumerate(self.peripherals):
                if peripheral.report_in_F13:
                    if peripheral.use_primary_thread and peripheral.auto_thread_lock:
                        peripheral.thread_lock.acquire()
                    try:
                        out_text += [peripheral.get_status_info()]
                    finally:
                        if peripheral.use_primary_thread and peripheral.auto_thread_lock:
                            peripheral.thread_lock.release()

        #out_text += ['jinsi_GCONF: 000001dc qiehuan_GCONF: 000001dc'] # Z-Mod doesn't actually use these, so removed them

        self.send_printer(' '.join(out_text))

    def update_timeout(self):
        if self.printer_connected_timeout > 0 and self.printer_connected_timeout_expire:
            if time.ticks_diff(self.printer_connected_timeout_expire, time.ticks_ms()) < 0:
                self.console.print("Printer disconnected", 'info')
                self.printer_connected_timeout_expire = None
                for peripheral in self.peripherals:
                    if peripheral.use_primary_thread and peripheral.auto_thread_lock:
                        peripheral.thread_lock.acquire()
                    try:
                        peripheral.timeout()
                    finally:
                        if peripheral.use_primary_thread and peripheral.auto_thread_lock:
                            peripheral.thread_lock.release()

    def run(self):
        self.started = True
        update_peripheral_index = 0
        while not self.comm.started:
            pass
        if self.printer_comm:
            while self.printer_comm.check_receive(): 
                self.printer_comm.receive() # Clear any that came in before core was ready
        while not self.terminate:
            try:
                self.update_printer()
                self.update_mmu()
                self.update_timeout()

                if len(self.peripherals) > 0:
                    if update_peripheral_index >= len(self.peripherals):
                        update_peripheral_index = 0
                    else:
                        if not self.peripherals[update_peripheral_index].use_primary_thread:
                            self.peripherals[update_peripheral_index].update()
                        update_peripheral_index += 1
            except KeyboardInterrupt:
                self.terminate = True
            except Exception as e:
                self.console.print_exception(e, 'core')

            if self.comm.terminate:
                self.terminate = True

        for peripheral in self.peripherals:
            try:
                if peripheral.use_primary_thread and peripheral.auto_thread_lock:
                    peripheral.thread_lock.acquire()
                try:
                    peripheral.shutdown()
                finally:
                    if peripheral.use_primary_thread and peripheral.auto_thread_lock:
                        peripheral.thread_lock.release()
            except Exception as e:
                self.console.print_exception(e)

        self.finished = True