from ij_comm_base import IJCI_Base
import _thread
import time
from ij_console import console
from ij_misc import get_traceback_string

_comms: IJ_Comms = None # type: ignore

def comms() -> IJ_Comms:
    global _comms
    if _comms is None:
        _comms = IJ_Comms()
    return _comms

class IJ_Comms:
    def __init__(self):
        self.comm_interfaces: dict[str, IJCI_Base] = None # type: ignore
        self.terminate = False
        self.finished = False
        self.full_error_details = True

    def run(self):
        _thread.start_new_thread(self._run, ())

    def _run(self):
        while not self.terminate:
            for interface in self.comm_interfaces.values():
                try:
                    interface.update()
                except KeyboardInterrupt:
                    raise
                except Exception as e:
                    console().write(f'Comms thread exception: {e}', 'error')
                    if self.full_error_details:
                        for line in get_traceback_string(e):
                            console().write(line, 'error')
                time.sleep_ms(1)
        self.finished = True