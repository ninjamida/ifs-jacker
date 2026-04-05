SCRIPT_IDENTIFIER = 'IFS Jacker'
SCRIPT_AUTHOR = 'Namida Verasche (Trumble)'
SCRIPT_VERSION = '2.0.0'

from core import IJ_Core
from comm import IJ_Comm_Manager
from console import get_console
from config import load_config
import time

def main():
    console = get_console()

    console.print(f'{SCRIPT_IDENTIFIER} version {SCRIPT_VERSION}', '')
    console.print(f'Author: {SCRIPT_AUTHOR}', '')
    console.print('', '')

    try:
        core = IJ_Core()
        comm = IJ_Comm_Manager()
        core.comm = comm
        comm.core = core

        load_config(core, comm)

        console.print('Starting core on second thread', 'info')
        console.flush()
        core.start_thread()

        console.print('Starting comms on primary thread', 'info')
        console.flush()
        comm.run()
    except Exception as e:
        console.print_exception(e, 'startup')
        console.flush()

    console.print('Terminating IFS Jacker', 'info')

    if comm.started and not comm.finished:
        console.print('Waiting for comms to exit', 'info')
        comm.terminate = True
    else:
        comm.finished = True
    
    if core.started and not core.finished:
        console.print('Waiting for core to exit', 'info')
        core.terminate = True
    else:
        core.finished = True
    
    reported_comm_finish = False
    reported_core_finish = False
    while not (reported_core_finish and reported_comm_finish):
        if comm.finished and not reported_comm_finish:
            if comm.started:
                console.print('Comms terminated', 'info')
            reported_comm_finish = True
        if core.finished and not reported_core_finish:
            if core.started:
                console.print('Core terminated', 'info')
            reported_core_finish = True

    console.print('IFS Jacker terminated', '')
    console.flush()

main()