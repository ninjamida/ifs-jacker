import machine, gc
from ij_core import IJ_Core
from ij_console import CONSOLE_THREADED
from ij_config import IJ_Config_Loader

def main():
    core = IJ_Core()
    IJ_Config_Loader().load_config(core)
    gc.collect()

    if CONSOLE_THREADED and core.console:
        core.console.start_thread()

    while not core.terminate:
        core.update()
    
    if CONSOLE_THREADED and core.console:
        core.console.terminate = True
        while core.console.running:
            pass

    if core.reboot_flag:
        machine.reset()

main()