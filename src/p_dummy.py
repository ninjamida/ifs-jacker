# Dummy peripheral.
#
# This is intended to fill gaps in your peripheral list if you want to remove one but don't want
# to update your configuration on the printer.
#
# No config params, no commands (except the generic ones), always returns status code 0.

from peripheral import IJ_Peripheral
from comm import _IJ_Comm_Abstract

class IJP_Dummy(IJ_Peripheral):
    def __init__(self):
        super().__init__()
        self.identifier = 'Dummy Peripheral'
        self.report_in_F13 = False
        self.report_in_Z4 = False
    
    @staticmethod
    def create(config_data: dict[str, str], all_comms: list[_IJ_Comm_Abstract]):
        return IJP_Dummy()
