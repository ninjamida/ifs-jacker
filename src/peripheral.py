import _thread

# Peripheral code should follow the following naming conventions, using "example" as an example name:
#  File name: p_example.py [must be lowercase]
#  Class name: IJP_Example ["IJP" is case-sensitive, "Example" is not]
#
# Conventions for commands:
#  F parameter specifies the command itself. Three values are reserved:
#     F0 - Should never be a valid command
#     F1 - Peripheral identification. Returns self.identifier. Replicate exactly, or pass via super() to
#          this class.
#     F2 - Peripheral status. Returns a string beginning with "F2 peripheral ok." Remainder of the response
#          can be as desired but should be used for this purpose.
#  L and S are open-purpose and can be used as you see fit. L should be considered the "primary" one (used
#  if only one is needed, etc).
#  C is not available, as it is used by Z5 (send command to peripheral) to indicate which peripheral to use.
#  Responses to commands should begin with (using F1 for example) "F1 peripheral ok."
#
#  Do not rely on default parameter values in handle_command's definition; as it may be called with 0
#  explicitly specified for values that were not provided in the incoming command.

class IJ_Peripheral:
    def __init__(self):
        self.use_primary_thread = False
        self.auto_thread_lock = True
        self.thread_lock = _thread.allocate_lock()
        self.identifier = 'Unknown Peripheral'
        self.report_in_F13 = True
        self.report_in_Z4 = True
        self.index = -1

    def update(self): # Runs frequently while idle.
        pass

    def initialize(self): # Runs once. Thread safety isn't needed here as only one thread is active when this is called.
        pass

    def shutdown(self): # Runs when IFS Jacker is shutting down. Thread safety is still needed.
        pass

    def timeout(self): # Runs if the connection to the printer times out.
        pass

    def activate(self): # Runs when the connection to the printer becomes active (at first startup or reconnecting after a timeout)
        pass

    def handle_command(self, f=0, l=0, s=0) -> str:
        if f == 1:
            return 'F1 peripheral ok. f{self.identifier}'
        if f == 2:
            return "F2 peripheral ok. No data"

        return f'F{f} peripheral ok. Unknown command'

    def get_status_info(self) -> str:
        return ''