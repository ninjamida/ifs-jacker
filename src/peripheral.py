import _thread

# Peripheral code should follow the following naming conventions, using "example" as an example name:
#  File name: p_example.py [must be lowercase]
#  Class name: IJP_Example ["IJP" is case-sensitive, "Example" is not]
#
# For those that run on the primary thread, IJ_Core will lock the thread before calling get_status_code.
# However, it will NOT do so for handle_command (as not all commands require this).
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
        self.thread_lock = _thread.allocate_lock()
        self.identifier = 'Unknown Peripheral'
        self.report_in_F13 = False
        self.report_in_Z4 = False

    def update(self):
        pass

    def handle_command(self, f=0, l=0, s=0) -> str:
        if f == 1:
            return 'F1 peripheral ok. f{self.identifier}'
        if f == 2:
            return "F2 peripheral ok. No data"
        
        return f'F{f} peripheral ok. Unknown command'

    def get_status_code(self) -> int:
        return 0