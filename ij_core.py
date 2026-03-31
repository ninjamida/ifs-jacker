from ij_printer_base import IJP_Base
from ij_mmu_base import IJM_Base
from ij_console import IJ_Console, CONSOLE_THREADED
from ij_command_conversion import command_dict_to_str, command_str_to_dict

SCRIPT_IDENTIFIER = 'IFS Jacker'
SCRIPT_AUTHOR = 'Namida Verasche (Trumble)'
SCRIPT_VERSION = '0.70'

class IJ_Core:   
    def __init__(self):
        self.printer: IJP_Base | None = None
        self.mmu: IJM_Base | None = None
        self.console: IJ_Console | None = None

        self.next_command: dict[str, str] | None = None
        self.next_command_origin: str = ''
        
        self.terminate = False

    def write_console(self, text: str | None):
        if self.console and text:
            self.console.lock()
            try:
                self.console.incoming += [text]
            finally:
                self.console.release()

    def update(self):
        if self.terminate:
            return

        try:
            if self.console and not CONSOLE_THREADED:
                self.console.execute()
            
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
        if self.console:
            if len(self.console.outgoing) > 0:
                self.console.lock()
                try:
                    new_cmd = self.console.outgoing.pop(0)
                    new_cmd = command_str_to_dict(new_cmd)
                    if new_cmd != None:
                        self.next_command = new_cmd
                        self.next_command_origin = 'console'
                        return
                except:
                    pass
                finally:
                    self.console.release()

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

        self.send_command_to_targets(command, targets)

    def send_command_to_targets(self, command: dict[str, str], targets: list[str]):
        if 'console' in targets and self.console:
            self.write_console(command_dict_to_str(command))
        
        if 'printer' in targets and self.printer:
            self.printer.send_response(command)

        if 'mmu' in targets and self.mmu:
            self.mmu.send_command(command, False)


    def execute_command_ij_get_status(self, command: dict[str, str], origin: str):
        response = {'command': 'ij_response_get_status'}

        response['script_identifier'] = SCRIPT_IDENTIFIER
        response['script_author'] = SCRIPT_AUTHOR
        response['script_version'] = SCRIPT_VERSION

        response['printer_type'] = type(self.printer).__name__ if self.printer is not None else 'None'
        response['mmu_type'] = type(self.mmu).__name__ if self.mmu is not None else 'None'
        response['channels'] = str(self.mmu.get_channel_count() if self.mmu else 0)

        self.next_command = response
        self.next_command_origin = f'response-{origin}'
            