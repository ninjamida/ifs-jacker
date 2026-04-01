from ij_mmu_base import IJM_Base
import time

class IJM_Splitter(IJM_Base):
    def __init__(self, mmu_list: list[IJM_Base]):
        super().__init__(None) # type: ignore
        self.mmu_list = mmu_list
        self.build_channel_map()
        self.last_used_mmu = 0
        self.mmu_recheck_frequency = 10 * 1000 # Every X ms, checks that the child MMU channel counts haven't changed. Unlikely to happen but not impossible, especially during initial startup.
        self.mmu_recheck_deadline = time.ticks_add(time.ticks_ms(), self.mmu_recheck_frequency)

        self.friendly_name = 'Splitter'
        for i, mmu in enumerate(self.mmu_list):
            self.friendly_name += f'__{i}_{mmu.friendly_name}'

    def build_channel_map(self):
        total_channels = 0
        self.channel_map = []
        self.channel_start_index = [-1] * len(self.mmu_list)
        self.cached_channel_counts = [-1] * len(self.mmu_list)
        for i, mmu in enumerate(self.mmu_list):
            self.channel_start_index[i] = total_channels
            self.cached_channel_counts[i] = mmu.get_channel_count()
            total_channels += self.cached_channel_counts[i]
            self.channel_map += [i] * (total_channels - len(self.channel_map))

    def get_channel_count(self) -> int:
        return len(self.channel_map)

    def receive_data(self, wait_timeout: float = 0) -> dict[str, str] | None:
        return self._receive_data(wait_timeout, False)

    def _receive_data(self, wait_timeout: float, raw: bool) -> dict[str, str] | None:
        if len(self.out_cmd_queue) > 0:
            return self.out_cmd_queue.pop(0)
        
        last_mmu = self.mmu_list[self.last_used_mmu]

        result = None

        if last_mmu.check_receive_data():
            result = last_mmu.receive_data()
            source_mmu = self.last_used_mmu
        else:
            for i, mmu in enumerate(self.mmu_list):
                if mmu != last_mmu and mmu.check_receive_data():
                    result = mmu.receive_data()
                    source_mmu = i
                    break
            if wait_timeout > 0 and result == None:
                result = last_mmu.receive_data(wait_timeout)
                source_mmu = self.last_used_mmu

        if raw:
            return result
        
        return self.adjust_channels(result, source_mmu)
        
    def adjust_channels(self, command: dict[str, str] | None, source_mmu: int) -> dict[str, str] | None:
        if command is None:
            return None

        if 'channel' in command:
            command['channel'] = str(int(command['channel']) + self.channel_start_index[source_mmu])
        
        if command.get('command', None) == 'mmu_respond_get_status':
            mmu = self.mmu_list[source_mmu]
            active_channel = int(command.get('active_channel', '-1'))
            if active_channel >= 0:
                command['active_channel'] = str(active_channel + self.channel_start_index[source_mmu])

            for key in command.keys():
                for i in reversed(range(mmu.get_channel_count())):
                    if key.startswith(f'channel_{i}'):
                        new_key = key.replace(f'channel_{i}', f'channel_{i + self.channel_start_index[source_mmu]}')
                        command[new_key] = command[key]
                        command.pop(key)                
        
        return command
        
    def check_receive_data(self) -> bool:
        for mmu in self.mmu_list:
            if mmu.check_receive_data():
                return True
        return False

    def send_command(self, command: dict[str, str], wait_for_response: bool = True) -> dict[str, str] | None:
        command_action = command.get('command', None)
        if command_action == None:
            return None
        handle_function = getattr(self, f'handle_out_{command_action}', None)
        if handle_function == None:
            return None
        else:
            return handle_function(command, wait_for_response)
        
    def update(self):
        if time.ticks_diff(self.mmu_recheck_deadline, time.ticks_ms()) < 0:
            need_redo = False
            for i in range(len(self.mmu_list)):
                if self.mmu_list[i].get_channel_count() != self.cached_channel_counts[i]:
                    need_redo = True
                    break
            
            if need_redo:
                self.build_channel_map()

            self.mmu_recheck_deadline = time.ticks_add(time.ticks_ms(), self.mmu_recheck_frequency)

    def get_plugin_status(self, response: dict[str, str]):
        super().get_plugin_status(response)
        response['mmu_count'] = str(len(self.mmu_list))
        response['last_used_mmu'] = str(self.last_used_mmu)

        for i, mmu in enumerate(self.mmu_list):
            this_response = {}
            mmu.get_plugin_status(this_response)
            for key, value in this_response.items():
                response[f'mmu{i}_{key}'] = value
    
    @staticmethod
    def make_from_config(config_data: dict[str, str], connection = None, key_prefix: str = '', load_mmu_func = None) -> IJM_Splitter:
        mmus = []
        if load_mmu_func:
            mmu_count = 0
            while config_data.get(f'{key_prefix}{mmu_count}_type', None):
                mmus += [load_mmu_func(config_data, f'{key_prefix}{mmu_count}_')]
                mmu_count += 1
        return IJM_Splitter(mmus)

    def _handle_out_channel_based(self, command: dict[str, str], wait_for_response: bool) -> dict[str, str] | None:
        channel = command.get('channel', None)
        if channel == None:
            return None
        channel = int(channel)
        if channel < 0 or channel > self.get_channel_count():
            return None
        mmu_index = self.channel_map[channel]
        channel -= self.channel_start_index[mmu_index]
        command['channel'] = str(channel)

        self.last_used_mmu = mmu_index
        result = self.mmu_list[mmu_index].send_command(command, wait_for_response)
        result = self.adjust_channels(result, mmu_index)

        return result
    
    def _handle_out_send_all(self, command: dict[str, str], wait_for_response: bool) -> dict[str, str] | None:
        for i in range(len(self.mmu_list)):
            if i != self.last_used_mmu:
                self.mmu_list[i].send_command(command, True)
        
        return self.mmu_list[self.last_used_mmu].send_command(command, wait_for_response)

    def handle_out_mmu_insert_filament(self, command: dict[str, str], wait_for_response: bool) -> dict[str, str] | None:
        return self._handle_out_channel_based(command, wait_for_response)
    
    def handle_out_mmu_withdraw_filament(self, command: dict[str, str], wait_for_response: bool) -> dict[str, str] | None:
        return self._handle_out_channel_based(command, wait_for_response)
    
    def handle_out_mmu_get_status(self, command: dict[str, str], wait_for_response: bool) -> dict[str, str] | None:
        mmu_statuses = []
        for i, mmu in enumerate(self.mmu_list):
            new_status = mmu.send_command({'command': 'mmu_get_status'}, True)
            if new_status == None:
                new_status = {'command': 'mmu_response_get_status', 'global_state': 'ok', 'active_channel': '-1'}
            mmu_statuses += [self.adjust_channels(new_status, i)]
        
        # Copy anything starting with channel_ from ALL the MMUs. Anything else, only from the last used oned.

        result = {'command': 'mmu_response_get_status'}

        for key, value in mmu_statuses[self.last_used_mmu].items():
            if not key.startswith('channel_'):
                result[key] = value

        for status in mmu_statuses:
            for key, value in status.items():
                if key.startswith('channel_'):
                    result[key] = value

        if wait_for_response:
            return result
        else:
            self.out_cmd_queue.append(result)
    
    def handle_out_mmu_reset_drivers(self, command: dict[str, str], wait_for_response: bool) -> dict[str, str] | None:
        return self._handle_out_send_all(command, wait_for_response)
    
    def handle_out_mmu_release_all_channels(self, command: dict[str, str], wait_for_response: bool) -> dict[str, str] | None:
        return self._handle_out_send_all(command, wait_for_response)
    
    def handle_out_mmu_mark_active_channel(self, command: dict[str, str], wait_for_response: bool) -> dict[str, str] | None:
        self._handle_out_channel_based(command, wait_for_response)

    def handle_out_mmu_clamp_channel(self, command: dict[str, str], wait_for_response: bool) -> dict[str, str] | None:
        target_mmu = self.channel_map[int(command['channel'])]

        for i in range(len(self.mmu_list)):
            if i != target_mmu:
                self.mmu_list[i].send_command({'command': 'mmu_release_all_channels'}, True)

        self._handle_out_channel_based(command, wait_for_response)

    def handle_out_mmu_release_channel(self, command: dict[str, str], wait_for_response: bool) -> dict[str, str] | None:
        self._handle_out_channel_based(command, wait_for_response)
    
    def handle_out_mmu_halt_movement(self, command: dict[str, str], wait_for_response: bool) -> dict[str, str] | None:
        return self._handle_out_send_all(command, wait_for_response)


    