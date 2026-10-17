"""One normal desktop host per OS user, regardless of executable path/version.

Only a fixed show-window message crosses a user-scoped local socket. No pairing
keys, URLs, CLI arguments or camera controls are forwarded to another process.
"""
import ctypes
import hashlib
import os
import stat
import sys
import tempfile
import time
from pathlib import Path

from PySide6.QtCore import QObject, QLockFile, QStandardPaths, QTimer, Signal
from PySide6.QtNetwork import QLocalServer, QLocalSocket


def instance_directory():
    if sys.platform == "win32":
        return Path(QStandardPaths.writableLocation(QStandardPaths.GenericDataLocation)) / "NoSubStudio" / "instance"
    # A short, private path: macOS ignores Unix socket permission flags and has
    # a small socket-path limit. Directory ownership/mode protects this endpoint.
    return Path(tempfile.gettempdir()) / f"nosub-studio-{os.getuid()}"


def secure_directory(path):
    path.mkdir(mode=0o700, parents=True, exist_ok=True)
    info = path.lstat()
    if not stat.S_ISDIR(info.st_mode):
        raise RuntimeError("The application instance directory is not a regular directory.")
    if sys.platform != "win32" and (info.st_uid != os.getuid() or info.st_mode & 0o077):
        raise RuntimeError("The application instance directory is not private to this user.")


def allow_foreground(pid):
    if sys.platform == "win32" and 0 < pid < 0xffffffff:
        # Grant only the existing host, never ASFW_ANY. The launching process
        # normally has foreground activation rights; the background host may not.
        library = ctypes.WinDLL("user32", use_last_error=True)
        library.AllowSetForegroundWindow.argtypes = [ctypes.c_uint32]
        library.AllowSetForegroundWindow.restype = ctypes.c_int
        library.AllowSetForegroundWindow(pid)


class SingleInstance(QObject):
    show_requested = Signal()

    def __init__(self, parent=None, directory=None, namespace="com.ethem.nosubcam.desktop"):
        super().__init__(parent)
        self.directory = Path(directory) if directory is not None else instance_directory()
        secure_directory(self.directory)
        digest = hashlib.sha256((str(self.directory.resolve()) + namespace).encode()).hexdigest()[:20]
        self.endpoint = (f"NoSubStudio-{digest}" if sys.platform == "win32" else str(self.directory / "show.sock"))
        self.lock = QLockFile(str(self.directory / "host.lock"))
        self.lock.setStaleLockTime(0)  # Never evict a live host just because it is old.
        self.server = QLocalServer(self)
        self.server.setSocketOptions(QLocalServer.SocketOption.UserAccessOption)
        self.server.newConnection.connect(self.accept_connections)
        self.primary = False
        self.clients = set()
        self.pending_show = False
        self.handler = None
        self.show_requested.connect(self.dispatch_show)

    def acquire(self, timeout_ms=2500):
        if self.lock.tryLock(0):
            self.primary = True
            # Only the lock owner can remove a stale socket left after a crash.
            QLocalServer.removeServer(self.endpoint)
            if not self.server.listen(self.endpoint):
                self.close()
                raise RuntimeError("NoSub Studio could not create its local activation channel.")
            return True
        if self.lock.error() != QLockFile.LockError.LockFailedError:
            raise RuntimeError("NoSub Studio could not access its application instance lock.")
        deadline = time.monotonic() + timeout_ms / 1000
        while time.monotonic() < deadline:
            if self.notify_existing(max(1, int((deadline - time.monotonic()) * 1000))):
                return False
            time.sleep(0.05)
        # Fail closed: a busy/unresponsive existing host must not result in a
        # second receiver, credential-store access or duplicate camera session.
        raise RuntimeError("NoSub Studio is already running but is not responding yet. "
                           "Open it from the menu bar/system tray, or wait for startup to finish.")

    def notify_existing(self, timeout_ms):
        socket = QLocalSocket()
        socket.setReadBufferSize(64)
        deadline = time.monotonic() + timeout_ms / 1000
        def remaining():
            return max(1, int((deadline - time.monotonic()) * 1000))
        try:
            socket.connectToServer(self.endpoint)
            if not socket.waitForConnected(min(200, remaining())):
                return False
            while not socket.canReadLine():
                if not socket.waitForReadyRead(remaining()):
                    return False
            hello = bytes(socket.readLine(64)).strip().split(b":")
            if len(hello) != 2 or hello[0] != b"nosub1" or not hello[1].isdigit():
                return False
            allow_foreground(int(hello[1]))
            socket.write(b"show\n")
            if socket.bytesToWrite() and not socket.waitForBytesWritten(remaining()):
                return False
            while not socket.canReadLine():
                if not socket.waitForReadyRead(remaining()):
                    return False
            return bytes(socket.readLine(16)) == b"ok\n"
        finally:
            socket.abort()

    def bind(self, handler):
        self.handler = handler
        if self.pending_show:
            self.dispatch_show()

    def dispatch_show(self):
        if self.handler is None:
            self.pending_show = True
        else:
            self.pending_show = False
            self.handler()

    def accept_connections(self):
        while self.server.hasPendingConnections():
            socket = self.server.nextPendingConnection()
            if len(self.clients) >= 8:
                socket.abort()
                socket.deleteLater()
                continue
            self.clients.add(socket)
            socket.setReadBufferSize(64)
            socket.readyRead.connect(lambda client=socket: self.read_request(client))
            socket.disconnected.connect(lambda client=socket: self.release_client(client))
            timer = QTimer(socket)
            timer.setSingleShot(True)
            timer.timeout.connect(lambda client=socket: client.abort())
            timer.start(3000)
            socket.write(f"nosub1:{os.getpid()}\n".encode())
            self.read_request(socket)

    def read_request(self, socket):
        if socket not in self.clients:
            return
        if socket.canReadLine():
            if bytes(socket.readLine(64)) == b"show\n":
                self.show_requested.emit()
                socket.write(b"ok\n")
                socket.disconnectFromServer()
            else:
                socket.abort()
        elif socket.bytesAvailable() >= 64:
            socket.abort()

    def release_client(self, socket):
        self.clients.discard(socket)
        socket.deleteLater()

    def close(self):
        if not self.primary:
            return
        for socket in list(self.clients):
            socket.abort()
        self.server.close()
        QLocalServer.removeServer(self.endpoint)
        self.lock.unlock()
        self.primary = False


def needs_single_instance(demo=False, screenshot=None):
    return not demo and screenshot is None
