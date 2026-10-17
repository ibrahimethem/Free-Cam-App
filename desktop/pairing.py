"""Remember one receiver identity using OS credentials, never QSettings/plaintext."""
import re
import secrets
import sys

SERVICE = "com.ethem.nosubcam.pairing"
ACCOUNT = "desktop"


def secure_backend():
    # Select only audited OS backends; never a third-party/plaintext fallback.
    if sys.platform == "darwin":
        from keyring.backends.macOS import Keyring
        return Keyring()
    if sys.platform == "win32":
        from keyring.backends.Windows import WinVaultKeyring
        return WinVaultKeyring()
    raise RuntimeError("No supported secure credential store")


class PairingIdentity:
    def __init__(self, backend=None):
        self.backend = backend
        self._token = None
        self.persisted = False

    def token(self):
        if self._token is not None:
            return self._token
        candidate = secrets.token_hex(16)
        try:
            self.backend = self.backend or secure_backend()
            saved = self.backend.get_password(SERVICE, ACCOUNT)
            if saved is not None and not re.fullmatch(r"[0-9a-f]{32}", saved):
                raise ValueError("Unexpected credential format")
            if saved is None:
                self.backend.set_password(SERVICE, ACCOUNT, candidate)
            self._token = saved or candidate
            self.persisted = True
        except Exception:
            # A locked/denied store must not be replaced or copied into an .ini.
            # Keep a session-only key and make that limitation visible in the UI.
            self._token = candidate
            self.persisted = False
        return self._token

    def reset(self):
        replacement = secrets.token_hex(16)
        if self.backend is None:
            self.backend = secure_backend()
        # Persist first. If saving fails, the active pairing remains unchanged.
        self.backend.set_password(SERVICE, ACCOUNT, replacement)
        self._token = replacement
        self.persisted = True


class SessionCredentials:
    """In-memory backend for explicit demos/tests; never used as a disk fallback."""
    def __init__(self):
        self.value = None

    def get_password(self, service, account):
        return self.value

    def set_password(self, service, account, value):
        self.value = value
