from ij_comm_base import IJCI_Base
import _thread

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

    def run(self):
        _thread.start_new_thread(self._run, ())

    def _run(self):
        while not self.terminate:
            for interface in self.comm_interfaces.values():
                interface.update()
        self.finished = True