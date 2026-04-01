RUN_CORE_ON_SECOND_THREAD = True

from ij_printer_base import IJP_Base
from ij_mmu_base import IJM_Base
from ij_console import IJ_Console, console
from ij_comm_base import IJCI_Base
from ij_comm_debug import get_debug_comm_interfaces
from ij_command_conversion import command_dict_to_str, command_str_to_dict
from ij_info import SCRIPT_AUTHOR, SCRIPT_IDENTIFIER, SCRIPT_VERSION
import gc, os # for stats

if RUN_CORE_ON_SECOND_THREAD:
    import _thread

class IJ_Core:   
    def __init__(self):
        self.comm_interfaces: dict[str, IJCI_Base] = {}
        self.printer: IJP_Base | None = None
        self.mmu: IJM_Base | None = None

        self.next_command: dict[str, str] | None = None
        self.next_command_origin: str = ''
        
        self.terminate = False
        self.reboot_flag = True

        if RUN_CORE_ON_SECOND_THREAD:
            self.finished = False

    def write_console(self, text: str | None):
        if text:
            console().lock()
            try:
                console().incoming += [text]
            finally:
                console().release()

    if RUN_CORE_ON_SECOND_THREAD:
        def run_threaded(self):
            _thread.start_new_thread(self.run_threaded_main, ())

        def run_threaded_main(self):
            while not self.terminate:
                self.update()
            self.finished = True

    def update(self):
        if self.terminate:
            return

        try:
            if not RUN_CORE_ON_SECOND_THREAD:
                console().execute()
            
            if self.next_command == None:
                self.get_next_command()

            if self.next_command != None:
                cmd = self.next_command
                origin = self.next_command_origin
                self.next_command = None
                self.next_command_origin = ''
                self.execute_command(cmd, origin)
        except KeyboardInterrupt:
            raise
        except Exception as e:
            self.write_console(f"Exception occurred in core: {e}")

    def get_next_command(self):
        if len(console().outgoing) > 0:
            console().lock()
            try:
                new_cmd = console().outgoing.pop(0)
                new_cmd = command_str_to_dict(new_cmd)
                if new_cmd != None:
                    self.next_command = new_cmd
                    self.next_command_origin = 'console'
                    return
            except:
                pass
            finally:
                console().release()

        if self.printer:
            while self.printer.check_receive_commands():
                new_cmd = self.printer.receive_command()
                if new_cmd != None:
                    self.next_command = new_cmd
                    self.next_command_origin = 'printer'
                    return
        
        if self.mmu:
            while self.mmu.check_receive_data():
                new_cmd = self.mmu.receive_data()
                if new_cmd != None:
                    self.next_command = new_cmd
                    self.next_command_origin = 'mmu'
                    return

    def execute_command(self, command: dict[str, str], origin: str):
        if origin != 'console':
            targets = ['console']
        else:
            targets = []

        if origin == 'printer' or origin == 'console' or origin == 'response-mmu':
            cmd = command.get('command', None)
            if cmd != None:
                if cmd.startswith('mmu'):
                    targets += ['mmu']
                else:
                    handler = getattr(self, 'execute_command_' + cmd, None)
                    if handler:
                        handler(command, origin)

        if origin == 'mmu' or origin == 'response-printer':
            cmd = command.get('command', None)
            if cmd == None:
                return
            if cmd.startswith('mmu_response'):
                targets += 'printer'
            else:
                handler = getattr(self, 'execute_command_' + cmd, None)
                if handler:
                    handler(command, origin)

        self.send_command_to_targets(command, targets, origin)

    def send_command_to_targets(self, command: dict[str, str], targets: list[str], origin: str):
        if 'console' in targets:
            self.write_console(f'{origin} >> {command_dict_to_str(command)}')
        
        if 'printer' in targets and self.printer:
            self.printer.send_response(command)

        if 'mmu' in targets and self.mmu:
            self.mmu.send_command(command, False)

    def execute_command_ij_get_status(self, command: dict[str, str], origin: str):
        response = {'command': 'ij_response_get_status'}

        response['script_identifier'] = SCRIPT_IDENTIFIER
        response['script_author'] = SCRIPT_AUTHOR
        response['script_version'] = SCRIPT_VERSION

        response['printer_type'] = self.printer.friendly_name if self.printer is not None else 'None'
        response['mmu_type'] = self.mmu.friendly_name if self.mmu is not None else 'None'
        response['channels'] = str(self.mmu.get_channel_count() if self.mmu else 0)

        mem_alloc = gc.mem_alloc()
        response['memory_ram_before_collect'] = f'{mem_alloc}/{mem_alloc + gc.mem_free()}'
        if command.get('gc', 'False') == 'True':
            gc.collect()
            mem_alloc = gc.mem_alloc()
            response['memory_ram_after_collect'] = f'{mem_alloc}/{mem_alloc + gc.mem_free()}'
        fs_stats = os.statvfs('/') # type: ignore
        fs_size = fs_stats[2] * fs_stats[0]
        response['memory_storage'] = f'{fs_size - (fs_stats[3] * fs_stats[0])}/{fs_size}'

        response['console'] = 'Enabled' if console() is IJ_Console else 'Disabled'
        response['core_on_second_thread'] = 'Enabled' if RUN_CORE_ON_SECOND_THREAD else 'Disabled'

        self.next_command = response
        self.next_command_origin = f'response-{origin}'

    def execute_command_ij_get_channel_count(self, command: dict[str, str], origin: str):
        response = {'command': 'ij_response_get_channel_count'}
        response['channels'] = str(self.mmu.get_channel_count() if self.mmu else 0)

        self.next_command = response
        self.next_command_origin = f'response-{origin}'

    def execute_command_ij_echo(self, command: dict[str, str], origin: str):
        command['command'] = 'ij_response_echo'
        self.next_command = command
        self.next_command_origin = f'response-{origin}'

    def execute_command_ij_debug_input(self, command: dict[str, str], origin: str):
        input_data = command.get('data', '')
        target = get_debug_comm_interfaces().get(command.get('target', ''), None)
        if target:
            target.receive_queue.append(input_data)

    def execute_command_ij_get_debug_inputs(self, command: dict[str, str], origin: str):
        response = {'command': 'ij_response_get_debug_inputs'}
        inputs = ' '.join([f"'{name}'" for name in get_debug_comm_interfaces().keys()])
        response['inputs'] = inputs
        
        self.next_command = response
        self.next_command_origin = f'response-{origin}'

    def execute_command_ij_get_printer_status(self, command: dict[str, str], origin: str):
        response = {'command': 'ij_response_get_printer_status'}
        if self.printer:
            self.printer.get_plugin_status(response)
        else:
            response['type'] = 'None'
        
        self.next_command = response
        self.next_command_origin = f'response-{origin}'

    def execute_command_ij_get_mmu_status(self, command: dict[str, str], origin: str):
        response = {'command': 'ij_response_get_mmu_status'}
        if self.mmu:
            self.mmu.get_plugin_status(response)
        else:
            response['type'] = 'None'
        
        self.next_command = response
        self.next_command_origin = f'response-{origin}'

    def execute_command_ij_get_comm_status(self, command: dict[str, str], origin: str):
        response = {'command': 'ij_response_get_comm_status', 'interface': command.get('interface', '')}
        comm = self.comm_interfaces.get(command.get('interface', ''), None)
        if comm:
            comm.get_plugin_status(response)
        else:
            response['type'] = 'None'
        
        self.next_command = response
        self.next_command_origin = f'response-{origin}'

    def execute_command_ij_get_comm_interfaces(self, command: dict[str, str], origin: str):
        response = {'command': 'ij_response_get_comm_interfaces'}
        for key, value in self.comm_interfaces.items():
            response[key] = value.friendly_name

        self.next_command = response
        self.next_command_origin = f'response-{origin}'


    def execute_command_terminate(self, command: dict[str, str], origin: str):
        self.terminate = True
        self.reboot_flag = False

    def execute_command_reboot(self, command: dict[str, str], origin: str):
        self.terminate = True
        self.reboot_flag = True
            