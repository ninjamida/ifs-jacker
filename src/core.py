import _thread, re, time
from comm import _IJ_Comm_Abstract
from console import get_console
from util import SCRIPT_IDENTIFIER, SCRIPT_VERSION, SCRIPT_AUTHOR

class IJ_Core:
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

        self.status_mmu_id = 0
        self.active_mmu_id = 0
        self.last_send_mmu_id = 0

        self.force_present_mask = 0
        self.force_absent_mask = ~0

        self.timeout = 3 * 1000
        self.timeout_expire = None

        self.queued_F18 = []
        self.done_queued_F18_skip = False
        self.hide_next_response = False # if true, will send an F13 response instead

        self.peripherals = []
        self.update_peripheral_index = 0

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
            if self.timeout > 0:
                if self.timeout_expire is None:
                    self.console.print('Printer connected', 'info')
                    for peripheral in self.peripherals:
                        if peripheral.use_primary_thread and peripheral.auto_thread_lock:
                            peripheral.thread_lock.acquire()
                        try:
                            peripheral.activate()
                        finally:
                            if peripheral.use_primary_thread and peripheral.auto_thread_lock:
                                peripheral.thread_lock.release()
                self.timeout_expire = time.ticks_add(time.ticks_ms(), self.timeout)

            in_split = printer_incoming_data.split(' ')
            f = 0
            c = 0
            s = 0
            l = 0
            z = 0
            mmu = self.active_mmu_id
            for element in in_split:
                if len(element) > 1:
                    param = element[0]
                    if param == 'F': f = int(element[1:])
                    if param == 'C': c = int(element[1:])
                    if param == 'S': s = int(element[1:])
                    if param == 'L': l = int(element[1:])
                    if param == 'Z': z = int(element[1:])
            
            if z > 0:
                if z == 1:
                    self.send_printer('Z1 ok.')

                if z == 2:
                    data = ['Z2 ok.']
                    data += [f'software: "{SCRIPT_IDENTIFIER}"']
                    data += [f'version: "{SCRIPT_VERSION}"']
                    data += [f'author: "{SCRIPT_AUTHOR}"']
                    data += [f'ifs_count: {len(self.mmu_comms)}']
                    data += [f'channel_count: {len(self.mmu_comms) * 4}']
                    data += [f'peripheral_count: {len(self.peripherals)}']
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
                            data += [f'peripheral_{i}: {peripheral.get_status_code()}']
                    self.send_printer(' '.join(data))

                if z == 5:
                    if c >= 0 and c < len(self.peripherals):
                        peripheral = self.peripherals[c]
                        if peripheral.use_primary_thread and peripheral.auto_thread_lock:
                            peripheral.thread_lock.acquire()
                        try:
                            self.send_printer(self.peripherals[c].handle_command(f, l, s))
                        finally:
                            if peripheral.use_primary_thread and peripheral.auto_thread_lock:
                                peripheral.thread_lock.release()
                    else:
                        self.send_printer(f'Z5 ok. Invalid peripheral index {c}')

                if z == 99:
                    self.terminate = True
                    self.send_printer('Z99 ok. Terminating')

            if z == 0 and f > 0:    
                if c > 0:
                    mmu = (c - 1) // 4
                    c = ((c - 1) % 4) + 1
                    self.active_mmu_id = mmu
                    self.status_mmu_id = mmu
                if f == 18 or f == 24:
                    self.queued_F18 = list(range(len(self.mmu_comms)))
                    self.queued_F18.remove(mmu)
                    self.done_queued_F18_skip = False
                    self.status_mmu_id = mmu
                if f == 13:
                    if len(self.queued_F18) > 0 and self.done_queued_F18_skip:
                        mmu = self.queued_F18.pop(0)
                        f = 18
                        c = 0
                        s = 0
                        l = 0
                        self.hide_next_response = True
                        self.done_queued_F18_skip = False
                    else:
                        if len(self.queued_F18) > 0:
                            self.done_queued_F18_skip = True
                        if len(self.mmu_comms) > 0:
                            c = 0
                            s = 0
                            l = 0
                            mmu = self.status_mmu_id
                        else:
                            # If there are no MMUs, send an immediate response with fake data.
                            if self.include_channel_count_in_status:
                                self.send_printer('F13 ok. FFS_state: 5 silk_state: 0 chan: 0 ffs_channels_insert: 0 stall_state: 0 channel_count: 0 jinsi_GCONF: 00000000 qiehuan_GCONF: 00000000')
                            else:
                                self.send_printer('F13 ok. FFS_state: 5 silk_state: 0 chan: 0 ffs_channels_insert: 0 stall_state: 0 jinsi_GCONF: 00000000 qiehuan_GCONF: 00000000')

                elements = [f'F{f}']
                if c > 0:
                    elements.append(f'C{c}')
                    if s > 0 and l > 0:
                        elements.append(f'L{l} S{s}')
                elements.append('\r\n')
                self.send_mmu(' '.join(elements), mmu)

    def send_mmu(self, data: str, mmu: int):
        if len(self.mmu_comms) > 0:
            self.mmu_comms[mmu].send(data)
            self.console.print(f'mmu{mmu} << {data}', 'data')
            self.last_send_mmu_id = mmu

    def update_mmu(self):
        if len(self.mmu_comms) == 0:
            return
        mmu = self.mmu_comms[self.last_send_mmu_id]
        if mmu.check_receive():
            mmu_incoming_data = mmu.receive().strip()
            self.console.print(f'mmu{self.last_send_mmu_id} >> {mmu_incoming_data}', 'data')
        else:
            mmu_incoming_data = ''

        if len(mmu_incoming_data) > 0:
            cmd_id = int(mmu_incoming_data.split(' ', 1)[0][1:])

            if cmd_id == 13 or self.hide_next_response:
                if cmd_id == 13:
                    cmd_split = mmu_incoming_data.split(' ')

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

                    shift = self.last_send_mmu_id * 4
                    mask = ~(0b1111 << shift)
                    self.silk_state = (self.silk_state & mask) | (new_silk_state << shift)
                    self.channels_insert = (self.channels_insert & mask) | (new_channels_insert << shift)
                    self.stall_state = (self.stall_state & mask) | (new_stall_state << shift)

                    if self.last_send_mmu_id == self.active_mmu_id:
                        self.chan = new_chan + self.last_send_mmu_id * 4
                        if new_ffs_state in [7, 11, 12, 15, 18, 22, 23, 26, 29, 33, 34, 37, 40, 44, 45, 48]:
                            self.ffs_state = new_ffs_state + (self.last_send_mmu_id * 44) # 11 per channel
                        else:
                            self.ffs_state = new_ffs_state

                    self.silk_state &= self.force_absent_mask
                    self.silk_state |= self.force_present_mask

                self.hide_next_response = False

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
                                out_text += [f'peripheral_{i}: {peripheral.get_status_code()}']
                            finally:
                                if peripheral.use_primary_thread and peripheral.auto_thread_lock:
                                    peripheral.thread_lock.release()

                out_text += ['jinsi_GCONF: 000001dc qiehuan_GCONF: 000001dc']

                self.send_printer(' '.join(out_text))

                if self.last_send_mmu_id != self.active_mmu_id or self.ffs_state == 5:
                    self.status_mmu_id = (self.status_mmu_id + 1) % len(self.mmu_comms)
            else:
                mmu_incoming_data = re.sub(
                    r'(channel|chan) (\d+)', 
                    lambda c: f'{c.group(1)} {int(c.group(2)) + (self.last_send_mmu_id * 4)}', 
                    mmu_incoming_data
                )
                self.send_printer(mmu_incoming_data)

    def update_timeout(self):
        if self.timeout > 0 and self.timeout_expire:
            if time.ticks_diff(self.timeout_expire, time.ticks_ms()) < 0:
                self.console.print("Printer disconnected", 'info')
                self.timeout_expire = None
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