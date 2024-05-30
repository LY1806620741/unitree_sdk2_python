import ctypes
from ctypes import wintypes

kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)

INFINITE = wintypes.DWORD(-1).value
WAIT_FAILED = wintypes.DWORD(-1).value
WAIT_IO_COMPLETION = 192

# https://learn.microsoft.com/en-us/windows/win32/api/synchapi/nc-synchapi-ptimerapcroutine
PTIMERAPCROUTINE = ctypes.WINFUNCTYPE(
    None,            # no return value
    wintypes.LPVOID, # lpArgToCompletionRoutine
    wintypes.DWORD,  # dwTimerLowValue
    wintypes.DWORD,  # dwTimerHighValue
)

# https://learn.microsoft.com/en-us/windows/win32/api/synchapi/nf-synchapi-createwaitabletimerw
kernel32.CreateWaitableTimerW.restype = wintypes.HANDLE
kernel32.CreateWaitableTimerW.argtypes = (
    wintypes.LPVOID,  # lpTimerAttributes
    wintypes.BOOL,    # bManualReset
    wintypes.LPCWSTR, # lpTimerName
)

# https://learn.microsoft.com/zh-cn/windows/win32/api/synchapi/nf-synchapi-setwaitabletimer
kernel32.SetWaitableTimer.restype = wintypes.BOOL
kernel32.SetWaitableTimer.argtypes = (
    wintypes.HANDLE,         # hTimer
    wintypes.PLARGE_INTEGER, # lpDueTime
    wintypes.LONG,           # lPeriod
    PTIMERAPCROUTINE,        # pfnCompletionRoutine,
    wintypes.LPVOID,         # lpArgToCompletionRoutine
    wintypes.BOOL,           # fResume
)

# https://learn.microsoft.com/en-us/windows/win32/api/synchapi/nf-synchapi-cancelwaitabletimer
kernel32.CancelWaitableTimer.restype = wintypes.BOOL
kernel32.CancelWaitableTimer.argtypes = (
    wintypes.HANDLE, # hTimer
)

# https://learn.microsoft.com/en-us/windows/win32/api/synchapi/nf-synchapi-waitforsingleobjectex
kernel32.WaitForSingleObjectEx.restype = wintypes.DWORD
kernel32.WaitForSingleObjectEx.argtypes = (
    wintypes.HANDLE, # hHandle
    wintypes.DWORD,  # dwMilliseconds
    wintypes.BOOL,   # bAlertable
)

#https://learn.microsoft.com/en-us/windows/win32/api/handleapi/nf-handleapi-closehandle
kernel32.CloseHandle.restype = wintypes.BOOL
kernel32.CloseHandle.argtypes = (
    wintypes.HANDLE, # hObject
)

@PTIMERAPCROUTINE
def timer_callback(arg, timer_low, timer_high):
    print(f'CALLBACK: {timer_low / 1e7:.2f}')

def timer_init(due_time: float, period: float) -> int:
    due_time = wintypes.LARGE_INTEGER(-int(due_time * 10**7))
    period = int(period * 1000)
    handle = kernel32.CreateWaitableTimerW(None, True, None)
    if not handle:
        raise ctypes.WinError(ctypes.get_last_error())
    if not kernel32.SetWaitableTimer(
                handle, ctypes.byref(due_time), period,
                timer_callback, 0, True):
        kernel32.CloseHandle(handle)
        raise ctypes.WinError(ctypes.get_last_error())
    return handle

def test(count):
    h = timer_init(1, 5)
    try:
        for i in range(count * 2):
            result = kernel32.WaitForSingleObjectEx(h, INFINITE, True)
            if result == 0:
                print('WAIT: Successful')
            elif result == WAIT_IO_COMPLETION:
                print('WAIT: APC Executed\n')
            elif result == WAIT_FAILED:
                raise ctypes.WinError(ctypes.get_last_error())
            else:
                raise OSError(f'Unexpected wait result: {result}')
    finally:
        kernel32.CancelWaitableTimer(h)
        kernel32.CloseHandle(h)
        
        
test(3)