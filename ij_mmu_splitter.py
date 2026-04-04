from ij_mmu_base import IJM_Base
import time

# Limitations of splitter:
# - Doesn't receive live responses from MMUs; responses may be received but this is after the splitter responds.
# - "Get status" command works but may be slower to update than an actual MMU.
# - Only works with passive MMUs (or MMUs that will tolerate their active communication being ignored).
# - Another downstream IFS Jacker run through the splitter should work.

class IJM_Splitter(IJM_Base):
    def __init__(self, mmu_list: list[IJM_Base]):
        super().__init__(None) # type: ignore
        self.mmu_list = mmu_list
        self.build_channel_map()
        self.initialize_status()
        self.active_channel_mmu = 0
        self.last_commanded_mmu = 0
        self.mmu_recheck_frequency = 10 * 1000 # Every X ms, checks that the child MMU channel counts haven't changed. Unlikely to happen but not impossible, especially during initial startup.
        self.mmu_recheck_deadline = time.ticks_add(time.ticks_ms(), self.mmu_recheck_frequency)

        self.next_idle_mmu_check = 0
        self.idle_command_queue: list[tuple] = [] # mmu index (int), high priority (bool), command (dict[str, str])
        self.idle_command_wait = int(0.5 * 1000) # After this long with no response, it is assumed one is not coming
        self.idle_awaiting_response_type = ''
        self.next_idle_command_time = time.ticks_add(time.ticks_ms(), self.idle_command_wait)
        # Queued commands labelled "high priority" will not be overridden by the active status MMU checking

        self.friendly_name = 'MMU Splitter'
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

    def initialize_status(self):
        mmu_get_status_response = {'command': 'mmu_response_get_status'}
        mmu_get_status_response['global_state'] = 'ok'
        mmu_get_status_response['active_channel'] = '0'
        for i in range(self.get_channel_count()):
            channel_prefix = f'channel_{i}_'
            mmu_get_status_response[channel_prefix + 'present'] = 'False'
            mmu_get_status_response[channel_prefix + 'need_insert'] = 'False'
            mmu_get_status_response[channel_prefix + 'stall'] = 'False'

        self.mmu_get_status_response = mmu_get_status_response

    def set_active_channel_mmu(self, mmu_index: int):
        self.active_channel_mmu = mmu_index
        self.next_idle_mmu_check = mmu_index
        self.mmu_get_status_response['global_status'] = 'querying'

    def get_channel_count(self) -> int:
        return len(self.channel_map)

    def receive_data(self, wait_timeout: float = 0) -> dict[str, str] | None:
        return self._receive_data(wait_timeout, False)

    def _receive_data(self, wait_timeout: float, raw: bool) -> dict[str, str] | None:
        if len(self.out_cmd_queue) > 0:
            return self.out_cmd_queue.pop(0)
        
        return None
        
    def adjust_channels(self, command: dict[str, str] | None, source_mmu: int) -> dict[str, str] | None:
        if command is None:
            return None

        if 'channel' in command:
            command['channel'] = str(int(command['channel']) + self.channel_start_index[source_mmu])
        
        if command.get('command', None) == 'mmu_response_get_status' and self.channel_start_index[source_mmu] > 0:
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
        return len(self.out_cmd_queue) > 0

    def send_command(self, command: dict[str, str], wait_for_response: bool = True) -> dict[str, str] | None:
        command_action = command.get('command', None)
        if command_action == None:
            return None
        handle_function = getattr(self, f'handle_out_{command_action}', None)
        if handle_function == None:
            return None
        else:
            result = handle_function(command, wait_for_response)
            if wait_for_response:
                return result
            else:
                self.out_cmd_queue.append(result)
                return None
        
    def update(self):
        for mmu in self.mmu_list:
            if mmu.check_receive_data():
                command = mmu.receive_data()
                if command:
                    command_action = command.get('command', None)
                    if command_action:
                        if command_action == self.idle_awaiting_response_type:
                            self.idle_awaiting_response_type = ''
                            self.next_idle_command_time = time.ticks_ms()
                        handle_function = getattr(self, f'handle_in_{command_action}', None)
                        if handle_function:
                            handle_function(command)
            mmu.update()

        if time.ticks_diff(self.mmu_recheck_deadline, time.ticks_ms()) < 0:
            need_redo = False
            for i in range(len(self.mmu_list)):
                if self.mmu_list[i].get_channel_count() != self.cached_channel_counts[i]:
                    need_redo = True
                    break
            
            if need_redo:
                self.build_channel_map()

            self.mmu_recheck_deadline = time.ticks_add(time.ticks_ms(), self.mmu_recheck_frequency)

        self.process_idle_queue()
    
    def queue_command(self, target_mmu: int, high_priority: bool, command: dict[str, str], force_to_front: bool = False):
        insert_index = 0
        if force_to_front:
            high_priority = True
        elif high_priority:
            while insert_index < len(self.idle_command_queue) and self.idle_command_queue[insert_index][1]:
                insert_index += 1
        else:
            insert_index = len(self.idle_command_queue)

        self.idle_command_queue.insert(insert_index, (target_mmu, high_priority, command))

    def process_idle_queue(self):
        if time.ticks_diff(self.next_idle_command_time, time.ticks_ms()) > 0:
            return

        if len(self.idle_command_queue) > 0:
            next_target, next_high_priority, next_command = self.idle_command_queue[0]
            next_from_queue = True
        else:
            next_target, next_high_priority, next_command = 0, False, None
            next_from_queue = False

        if not next_high_priority and self.mmu_get_status_response['global_state'] != 'ok':
            next_target = self.active_channel_mmu
            next_command = {'command': 'mmu_get_status'}
            if self.next_idle_mmu_check == self.active_channel_mmu:
                self.next_idle_mmu_check += 1
            next_from_queue = False

        if next_command == None:
            self.next_idle_mmu_check %= len(self.mmu_list)
            next_target = self.next_idle_mmu_check
            self.next_idle_mmu_check += 1
            next_command = {'command': 'mmu_get_status'}
            next_from_queue = False

        if next_from_queue:
            self.idle_command_queue.pop(0)

        self.mmu_list[next_target].send_command(next_command, False)
        self.idle_awaiting_response_type = next_command.get('command', '').replace('mmu_', 'mmu_response_', 1)
        self.next_idle_command_time = time.ticks_add(time.ticks_ms(), self.idle_command_wait)
        self.last_commanded_mmu = next_target

    def update_get_status_response(self, command: dict[str, str] | None, mmu_index: int):
        command = self.adjust_channels(command, mmu_index)
        if command:
            for key, value in command.items():
                if mmu_index == self.active_channel_mmu or key.startswith('channel_'):
                    self.mmu_get_status_response[key] = value

    def get_plugin_status(self, response: dict[str, str]):
        super().get_plugin_status(response)
        response['mmu_count'] = str(len(self.mmu_list))
        response['active_channel_mmu'] = str(self.active_channel_mmu)

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

    def _handle_out_channel_based(self, command: dict[str, str], wait_for_response: bool, force_to_front: bool = False) -> dict[str, str] | None:
        channel = command.get('channel', None)
        if channel == None:
            return None
        channel = int(channel)
        if channel < 0 or channel > self.get_channel_count():
            return None
        mmu_index = self.channel_map[channel]
        channel -= self.channel_start_index[mmu_index]
        command['channel'] = str(channel)

        self.set_active_channel_mmu(mmu_index)
        self.queue_command(mmu_index, True, command, force_to_front)

        return {'command': command.get('command', '').replace('mmu_', 'mmu_response_', 1), 'channel': str(channel)}
    
    def _handle_out_send_all(self, command: dict[str, str], wait_for_response: bool, force_to_front: bool = False) -> dict[str, str] | None:
        self.queue_command(self.active_channel_mmu, True, command, force_to_front)
        for i in range(len(self.mmu_list)):
            if i != self.active_channel_mmu:
                self.queue_command(i, True, command)
        
        return {'command': command.get('command', '').replace('mmu_', 'mmu_response_', 1)}

    def handle_out_mmu_insert_filament(self, command: dict[str, str], wait_for_response: bool) -> dict[str, str] | None:
        return self._handle_out_channel_based(command, wait_for_response)
    
    def handle_out_mmu_withdraw_filament(self, command: dict[str, str], wait_for_response: bool) -> dict[str, str] | None:
        return self._handle_out_channel_based(command, wait_for_response)
    
    def handle_out_mmu_get_status(self, command: dict[str, str], wait_for_response: bool) -> dict[str, str] | None:
        self.mmu_get_status_response['channel_count'] = str(len(self.channel_map))
        return self.mmu_get_status_response
    
    def handle_out_mmu_reset_drivers(self, command: dict[str, str], wait_for_response: bool) -> dict[str, str] | None:
        return self._handle_out_send_all(command, wait_for_response)
    
    def handle_out_mmu_release_all_channels(self, command: dict[str, str], wait_for_response: bool) -> dict[str, str] | None:
        return self._handle_out_send_all(command, wait_for_response)
    
    def handle_out_mmu_mark_active_channel(self, command: dict[str, str], wait_for_response: bool) -> dict[str, str] | None:
        self._handle_out_channel_based(command, wait_for_response)

    def handle_out_mmu_clamp_channel(self, command: dict[str, str], wait_for_response: bool) -> dict[str, str] | None:
        target_mmu = self.channel_map[int(command['channel'])]

        self._handle_out_channel_based(command, wait_for_response)

        for i in range(len(self.mmu_list)):
            if i != target_mmu:
                self.idle_command_queue.append((i, True, {'command': 'mmu_release_all_channels'}))

    def handle_out_mmu_release_channel(self, command: dict[str, str], wait_for_response: bool) -> dict[str, str] | None:
        self._handle_out_channel_based(command, wait_for_response)
    
    def handle_out_mmu_halt_movement(self, command: dict[str, str], wait_for_response: bool) -> dict[str, str] | None:
        return self._handle_out_send_all(command, wait_for_response, True)
    
    def handle_in_mmu_response_get_status(self, command: dict[str, str]):
        self.adjust_channels(command, self.last_commanded_mmu)
        self.update_get_status_response(command, self.last_commanded_mmu)


    