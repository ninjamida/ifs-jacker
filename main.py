import machine, gc, time
from ij_core import IJ_Core, RUN_CORE_ON_SECOND_THREAD
from ij_config import IJ_Config_Loader
from ij_console import console

if RUN_CORE_ON_SECOND_THREAD:
    import _thread

def main():
    start_time = time.ticks_ms()

    core = IJ_Core()
    IJ_Config_Loader().load_config(core)
    gc.collect()

    console().incoming += ['IFS Jacker loaded']
    console().outgoing += ['ij_get_status']
    console().outgoing += [f'ij_echo load_time={time.ticks_diff(time.ticks_ms(), start_time)}ms']

    if RUN_CORE_ON_SECOND_THREAD:
        _thread.stack_size(8192)
        core.run_threaded()
        while not core.finished:
            console().execute()
    else:
        while not core.terminate:
            core.update()
            console().execute()

    if core.reboot_flag:
        machine.reset()

main()