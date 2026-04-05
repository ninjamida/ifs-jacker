import _thread, sys, uselect, re
from comm import _IJ_Comm_Abstract
from console import get_console

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
        self.home_mmu_id = 0
        self.last_send_mmu_id = 0

        self.force_present_mask = 0
        self.force_absent_mask = ~0

        self.include_channel_count_in_status = True

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
                self.console.print(f'printer >> {printer_incoming_data}', 'data')
            else:
                printer_incoming_data = ''

        if len(printer_incoming_data) > 0:
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

                if z == 99:
                    self.terminate = True
                    self.send_printer('Z99 ok. Terminating')

            if z == 0 and f > 0:    
                if c > 0:
                    mmu = (c - 1) // 4
                    c = ((c - 1) % 4) + 1
                    self.active_mmu_id = mmu
                    self.status_mmu_id = mmu
                    self.home_mmu_id = mmu
                if f == 13:
                    if len(self.mmu_comms) > 0:
                        c = 0
                        s = 0
                        l = 0
                        mmu = self.status_mmu_id
                    else:
                        if self.include_channel_count_in_status:
                            self.send_printer('F13 ok. FFS_state: 5 silk_state: 0 chan: 0 ffs_channels_insert: 0 stall_state: 0 channel_count: 0 jinsi_GCONF: 00000000 qiehuan_GCONF: 00000000')
                        else:
                            self.send_printer('F13 ok. FFS_state: 5 silk_state: 0 chan: 0 ffs_channels_insert: 0 stall_state: 0 jinsi_GCONF: 00000000 qiehuan_GCONF: 00000000')
                if f == 18:
                    mmu = self.home_mmu_id
                    self.home_mmu_id = (self.home_mmu_id + 1) % len(self.mmu_comms)

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

                out_text = [f'F13 ok. FFS_state: {self.ffs_state} silk_state: {self.silk_state} chan: {self.chan}']
                out_text += [f'ffs_channels_insert: {self.channels_insert} stall_state: {self.stall_state}']
                
                if self.include_channel_count_in_status:
                    out_text += [f'channel_count: {len(self.mmu_comms) * 4}']

                out_text += ['jinsi_GCONF: 000001dc qiehuan_GCONF: 000001dc']

                self.send_printer(' '.join(out_text))

                if self.last_send_mmu_id != self.active_mmu_id or new_ffs_state == 5:
                    self.status_mmu_id = (self.status_mmu_id + 1) % len(self.mmu_comms)
            else:
                mmu_incoming_data = re.sub(
                    r'(channel|chan) (\d+)', 
                    lambda c: f'{c.group(1)} {int(c.group(2)) + (self.last_send_mmu_id * 4)}', 
                    mmu_incoming_data
                )
                self.send_printer(mmu_incoming_data)

    def run(self):
        self.started = True
        while not self.terminate:
            try:
                self.update_printer()
                self.update_mmu()
            except KeyboardInterrupt:
                self.terminate = True
            except Exception as e:
                self.console.print_exception(e, 'core')

            if self.comm.terminate:
                self.terminate = True
                        
        self.finished = True