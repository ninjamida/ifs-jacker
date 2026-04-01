import machine, gc, time
from ij_core import IJ_Core
from ij_console import CONSOLE_THREADED
from ij_config import IJ_Config_Loader

def main():
    start_time = time.ticks_ms()

    core = IJ_Core()
    IJ_Config_Loader().load_config(core)
    gc.collect()

    if core.console:
        core.console.incoming += ['IFS Jacker loaded']
        core.console.outgoing += ['ij_get_status']
        core.console.outgoing += [f'ij_echo load_time={time.ticks_diff(time.ticks_ms(), start_time)}ms']

    if CONSOLE_THREADED and core.console:
        core.console.start_thread()

    try:
        while not core.terminate:
            core.update()
    finally:
        if CONSOLE_THREADED and core.console:
            core.console.terminate = True
            while core.console.running:
                pass

    if core.reboot_flag:
        machine.reset()

main()