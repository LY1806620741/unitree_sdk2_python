import math
import ctypes
import platform


# build platform compatible
if platform.system() == "Windows":
    from ctypes import wintypes
    kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)

    # 定义Windows API类型
    HANDLE = wintypes.HANDLE
    LARGE_INTEGER = wintypes.LARGE_INTEGER
    ULONG_PTR = wintypes.WPARAM
    ULONG = wintypes.UINT
    BOOL = wintypes.BOOL
    DWORD = wintypes.DWORD

    WAIT_FAILED = wintypes.DWORD(-1)
    WAIT_OBJECT_0 = wintypes.DWORD(0)  # 表示等待的对象已被信号所设置

    # 定义Windows API函数
    CreateWaitableTimer = kernel32.CreateWaitableTimerW
    CreateWaitableTimer.argtypes = (wintypes.LPVOID, BOOL, wintypes.LPCWSTR)
    CreateWaitableTimer.restype = HANDLE

    SetWaitableTimer = kernel32.SetWaitableTimer
    SetWaitableTimer.argtypes = (HANDLE, ctypes.POINTER(LARGE_INTEGER), ULONG, ULONG_PTR, ULONG_PTR, BOOL, DWORD)
    SetWaitableTimer.restype = BOOL

    WaitForSingleObject = kernel32.WaitForSingleObject
    WaitForSingleObject.argtypes = (HANDLE, DWORD)
    WaitForSingleObject.restype = DWORD

    CloseHandle = kernel32.CloseHandle
    CloseHandle.argtypes = (HANDLE,)
    CloseHandle.restype = BOOL

    INFINITE = DWORD(-1)
    INVALID_HANDLE_VALUE = HANDLE(-1)

    class TimerHandle:
        def __init__(self, handle=INVALID_HANDLE_VALUE):
            self.handle = handle

        def close(self):
            if self.handle != INVALID_HANDLE_VALUE:
                CloseHandle(self.handle)
                self.handle = INVALID_HANDLE_VALUE

        def __del__(self):
            self.close()

    def timerfd_create(clockid :int,ignoreflag :int):
        if clockid != 1:
            raise ctypes.WinError("not support clockid")
        handle = TimerHandle()
        handle.handle = CreateWaitableTimer(None, True, None)
        if not handle.handle:
            raise ctypes.WinError(ctypes.get_last_error())
        return handle

    def timerfd_settime_window(handle, ignoreflag :int, interval :float,period :float):
        # 秒转毫秒
        due_time = LARGE_INTEGER(int(interval * -10000))  # Convert ms to 100-nano-second intervals
        period = int(period * 10000) if period > 0 else None
        if not SetWaitableTimer(handle.handle, ctypes.byref(due_time), period, 0, 0, False, 0):
            raise ctypes.WinError(ctypes.get_last_error())
        
    def timerfd_settime(handle ,interval :float,value :float):
        timerfd_settime_window(handle, 0, interval, value)

    def timerfd_gettime(handle, timeout_ms=INFINITE):
        result = WaitForSingleObject(handle.handle, timeout_ms)
        if result == WAIT_FAILED:
            raise ctypes.WinError(ctypes.get_last_error())
        return result == WAIT_OBJECT_0
elif platform.system() == "Linux":
    
    from .clib_lookup import CLIBLookup

    class timespec(ctypes.Structure):
        _fields_ = [("sec", ctypes.c_long), ("nsec", ctypes.c_long)]
        __slots__ = [name for name,type in _fields_]

        @classmethod
        def from_seconds(cls, secs):
            c = cls()
            c.seconds = secs
            return c
        
        @property
        def seconds(self):
            return self.sec + self.nsec / 1000000000

        @seconds.setter
        def seconds(self, secs):
            x, y = math.modf(secs)
            self.sec = int(y)
            self.nsec = int(x * 1000000000)


    class itimerspec(ctypes.Structure):
        _fields_ = [("interval", timespec),("value", timespec)]
        __slots__ = [name for name,type in _fields_]
        
        @classmethod
        def from_seconds(cls, interval, value):
            spec = cls()
            spec.interval.seconds = interval
            spec.value.seconds = value
            return spec


    # function timerfd_create
    timerfd_create = CLIBLookup("timerfd_create", ctypes.c_int, (ctypes.c_long, ctypes.c_int))

    # function timerfd_settime
    timerfd_settime_linux = CLIBLookup("timerfd_settime", ctypes.c_int, (ctypes.c_int, ctypes.c_int, ctypes.POINTER(itimerspec), ctypes.POINTER(itimerspec)))

    def timerfd_settime(handle,interval,value):
        spec = itimerspec.from_seconds(interval, value)
        timerfd_settime_linux(handle, 0, spec, None)

    # function timerfd_gettime
    timerfd_gettime = CLIBLookup("timerfd_gettime", ctypes.c_int, (ctypes.c_int, ctypes.POINTER(itimerspec)))
    def timerfd_gettime(handle , timeout):
        import os
        os.read(handle, 8)