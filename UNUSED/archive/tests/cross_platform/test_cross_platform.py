import sys
import os
import pytest
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from utils.cross_platform import get_active_window_info

@pytest.mark.skipif(sys.platform != "win32", reason="Only runs on Windows.")
def test_get_active_window_info_windows():
    info = get_active_window_info()
    assert info is None or (
        isinstance(info, dict)
        and "app_name" in info
        and "window_title" in info
        and "pid" in info
        and "timestamp" in info
    )

# Example of how to mock for CI or non-Windows
from unittest import mock

def test_get_active_window_info_mock():
    import utils.cross_platform
    import types
    # Ensure module-level variables exist for patching
    if utils.cross_platform.psutil is None:
        utils.cross_platform.psutil = types.SimpleNamespace(Process=None)
    if utils.cross_platform.win32gui is None:
        utils.cross_platform.win32gui = types.SimpleNamespace(GetForegroundWindow=None, GetWindowText=None)
    if utils.cross_platform.win32process is None:
        utils.cross_platform.win32process = types.SimpleNamespace(GetWindowThreadProcessId=None)
    with mock.patch("utils.cross_platform.sys.platform", "win32"), \
         mock.patch("utils.cross_platform.win32gui.GetForegroundWindow", return_value=123), \
         mock.patch("utils.cross_platform.win32gui.GetWindowText", return_value="Test Window"), \
         mock.patch("utils.cross_platform.win32process.GetWindowThreadProcessId", return_value=(0, 456)), \
         mock.patch("utils.cross_platform.psutil.Process") as MockProcess:
        MockProcess.return_value.name.return_value = "test.exe"
        from utils.cross_platform import get_active_window_info
        info = get_active_window_info()
        assert info["app_name"] == "test.exe"
        assert info["window_title"] == "Test Window"
        assert info["pid"] == "456"
