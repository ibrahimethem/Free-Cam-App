"""Real local IPC/lock checks, without a receiver, Keychain, camera or tray."""
import os
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QCoreApplication
from PySide6.QtNetwork import QLocalSocket
from single_instance import SingleInstance, allow_foreground, needs_single_instance

APP = QCoreApplication.instance() or QCoreApplication([])


class InstanceTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.directory = Path(self.temporary.name)
        self.primary = SingleInstance(directory=self.directory)

    def tearDown(self):
        self.primary.close()
        APP.processEvents()
        self.temporary.cleanup()

    def peer(self, mode="--peer"):
        return subprocess.Popen([sys.executable, str(Path(__file__).resolve()), mode, str(self.directory)],
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

    def finish(self, child):
        deadline = time.monotonic() + 6
        while child.poll() is None and time.monotonic() < deadline:
            APP.processEvents()
            time.sleep(0.01)
        if child.poll() is None:
            child.kill()
            child.communicate()
            self.fail("Test-only secondary process did not finish")
        output, errors = child.communicate()
        self.assertEqual(child.returncode, 0, errors)
        return output

    def test_secondary_activates_primary_without_acquiring_lock(self):
        requests = []
        self.primary.bind(lambda: requests.append("show"))
        self.assertTrue(self.primary.acquire())
        self.assertIn("secondary", self.finish(self.peer()))
        self.assertEqual(requests, ["show"])
        self.assertTrue(self.primary.primary)
        self.assertTrue(self.primary.lock.isLocked())

    def test_multiple_launches_only_request_window_activation(self):
        requests = []
        self.primary.bind(lambda: requests.append("show"))
        self.assertTrue(self.primary.acquire())
        for _ in range(3):
            self.finish(self.peer())
        self.assertEqual(len(requests), 3)

    def test_activation_during_startup_is_delivered_after_window_binds(self):
        self.assertTrue(self.primary.acquire())
        self.finish(self.peer())
        self.assertTrue(self.primary.pending_show)
        requests = []
        self.primary.bind(lambda: requests.append("show"))
        self.assertEqual(requests, ["show"])
        self.assertFalse(self.primary.pending_show)

    def test_normal_quit_releases_lock_for_next_launch(self):
        self.assertTrue(self.primary.acquire())
        self.primary.close()
        other = SingleInstance(directory=self.directory)
        try:
            self.assertTrue(other.acquire())
        finally:
            other.close()

    def test_crashed_test_process_does_not_leave_a_permanent_lock(self):
        child = self.peer("--own")
        try:
            deadline = time.monotonic() + 5
            while not (self.directory / "host.lock").exists() and time.monotonic() < deadline and child.poll() is None:
                time.sleep(0.01)
            self.assertTrue((self.directory / "host.lock").exists())
        finally:
            child.kill()
            child.communicate()
        self.assertTrue(self.primary.acquire())

    def test_unknown_message_does_not_activate_or_control_host(self):
        requests = []
        self.primary.bind(lambda: requests.append("show"))
        self.assertTrue(self.primary.acquire())
        self.finish(self.peer("--invalid"))
        self.assertEqual(requests, [])

    def test_busy_unresponsive_primary_never_allows_another_host(self):
        self.assertTrue(self.primary.acquire())
        # Same thread deliberately does not process the primary event loop.
        other = SingleInstance(directory=self.directory)
        with self.assertRaisesRegex(RuntimeError, "already running"):
            other.acquire(timeout_ms=80)
        self.assertFalse(other.primary)

    def test_demo_and_screenshot_are_explicitly_independent(self):
        self.assertTrue(needs_single_instance())
        self.assertFalse(needs_single_instance(demo=True))
        self.assertFalse(needs_single_instance(screenshot=Path("test.png")))

    def test_windows_foreground_grant_never_uses_any_process_or_overflows(self):
        with patch("single_instance.sys.platform", "win32"), patch("single_instance.ctypes.WinDLL", create=True) as dll:
            for pid in (-1, 0, 0xffffffff, 0x1ffffffff):
                allow_foreground(pid)
            dll.assert_not_called()


def child_main():
    mode, directory = sys.argv[1:]
    guard = SingleInstance(directory=directory)
    if mode == "--invalid":
        socket = QLocalSocket()
        socket.connectToServer(guard.endpoint)
        if not socket.waitForConnected(1000):
            return 3
        socket.write(b"quit\n")  # Unsupported, even for another same-user app.
        socket.waitForBytesWritten(1000)
        socket.waitForDisconnected(1000)
        return 0
    try:
        primary = guard.acquire()
        if mode == "--own":
            return APP.exec() if primary else 4
        print("primary" if primary else "secondary")
        return 2 if primary else 0
    finally:
        guard.close()


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] in ("--peer", "--own", "--invalid"):
        sys.exit(child_main())
    unittest.main()
