import unittest
from unittest.mock import MagicMock, patch

from pairing import PairingIdentity, SessionCredentials, SERVICE, ACCOUNT


class PairingTests(unittest.TestCase):
    def test_identity_survives_new_instances_and_receiver_restarts(self):
        backend = SessionCredentials()
        first = PairingIdentity(backend)
        token = first.token()
        self.assertEqual(len(token), 32)
        self.assertEqual(first.token(), token)
        self.assertEqual(PairingIdentity(backend).token(), token)
        self.assertTrue(first.persisted)

    def test_explicit_reset_replaces_the_saved_identity(self):
        backend = SessionCredentials()
        identity = PairingIdentity(backend)
        old = identity.token()
        identity.reset()
        self.assertNotEqual(identity.token(), old)
        self.assertEqual(PairingIdentity(backend).token(), identity.token())

    def test_failed_read_never_overwrites_a_locked_store(self):
        backend = MagicMock()
        backend.get_password.side_effect = RuntimeError("Locked")
        identity = PairingIdentity(backend)
        self.assertEqual(identity.token(), identity.token())
        self.assertFalse(identity.persisted)
        backend.set_password.assert_not_called()

    def test_failed_save_uses_memory_only(self):
        backend = MagicMock()
        backend.get_password.return_value = None
        backend.set_password.side_effect = RuntimeError("Denied")
        identity = PairingIdentity(backend)
        self.assertEqual(len(identity.token()), 32)
        self.assertFalse(identity.persisted)

    def test_failed_reset_keeps_the_current_identity(self):
        backend = MagicMock()
        backend.get_password.return_value = "a" * 32
        identity = PairingIdentity(backend)
        original = identity.token()
        backend.set_password.side_effect = RuntimeError("Denied")
        with self.assertRaises(RuntimeError):
            identity.reset()
        self.assertEqual(identity.token(), original)

    def test_corrupt_stored_data_is_not_silently_replaced(self):
        backend = MagicMock()
        backend.get_password.return_value = "invalid"
        identity = PairingIdentity(backend)
        identity.token()
        self.assertFalse(identity.persisted)
        backend.set_password.assert_not_called()

    def test_explicit_backend_does_not_probe_real_user_credentials(self):
        with patch("pairing.secure_backend") as secure:
            identity = PairingIdentity(SessionCredentials())
            identity.token()
            secure.assert_not_called()


if __name__ == "__main__":
    unittest.main()
