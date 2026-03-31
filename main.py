import machine
from ij_core import IJ_Core
from ij_console import IJ_Console, CONSOLE_THREADED

def main():
    core = IJ_Core()
    
    console = IJ_Console()
    core.console = console

    if CONSOLE_THREADED:
        console.start_thread()

    while not core.terminate:
        core.update()
    
    if CONSOLE_THREADED:
        console.terminate = True
        while console.running:
            pass

    if core.reboot_flag:
        machine.reset()

main()