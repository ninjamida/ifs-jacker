import machine, gc, time
from ij_core import IJ_Core
from ij_config import IJ_Config_Loader
from ij_console import console
from ij_comms import comms

def main():
    start_time = time.ticks_ms()

    core = IJ_Core()
    IJ_Config_Loader().load_config(core)
    gc.collect()

    console().incoming += ['IFS Jacker loaded']
    console().outgoing += ['ij_get_status']
    console().outgoing += [f'ij_echo load_time={time.ticks_diff(time.ticks_ms(), start_time)}ms']

    comms().run()

    while not core.terminate:
        core.update()
        console().execute()

    comms().terminate = True
    while not comms().finished:
        pass

    if core.reboot_flag:
        machine.reset()

main()