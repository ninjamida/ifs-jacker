import machine, gc, time
from ij_core import IJ_Core, RUN_CORE_ON_SECOND_THREAD
from ij_config import IJ_Config_Loader
from ij_console import console

def main():
    start_time = time.ticks_ms()

    core = IJ_Core()
    IJ_Config_Loader().load_config(core)
    gc.collect()

    if console:
        console.incoming += ['IFS Jacker loaded']
        console.outgoing += ['ij_get_status']
        console.outgoing += [f'ij_echo load_time={time.ticks_diff(time.ticks_ms(), start_time)}ms']

    if RUN_CORE_ON_SECOND_THREAD and console:
        core.run_threaded()
        while not core.finished:
            console.execute()
    else:
        while not core.terminate:
            core.update()

    if core.reboot_flag:
        machine.reset()

main()