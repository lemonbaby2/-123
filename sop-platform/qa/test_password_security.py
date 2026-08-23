from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path


_IMPORT_RUNTIME = tempfile.TemporaryDirectory()
os.environ["SOP_RUNTIME_DIR"] = _IMPORT_RUNTIME.name
TEST_INITIAL_PASSWORD = "test-initial-8113"
os.environ["SOP_INITIAL_PASSWORD"] = TEST_INITIAL_PASSWORD
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import server


class PasswordSecurityTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        root = Path(self.temporary.name)
        self.original_runtime = server.RUNTIME_ROOT
        self.original_db = server.ANNOTATION_DB_PATH
        server.RUNTIME_ROOT = root
        server.ANNOTATION_DB_PATH = root / "annotations.sqlite3"
        server.initialize_annotation_db()
        os.environ["SOP_PASSWORD_RECOVERY_CODE"] = "local-recovery-code"

    def tearDown(self) -> None:
        server.RUNTIME_ROOT = self.original_runtime
        server.ANNOTATION_DB_PATH = self.original_db
        os.environ.pop("SOP_PASSWORD_RECOVERY_CODE", None)
        self.temporary.cleanup()

    def test_initial_password_can_authenticate_all_roles(self) -> None:
        for username in ("admin", "manager", "worker"):
            self.assertIsNotNone(server.authenticate_user(username, TEST_INITIAL_PASSWORD))

    def test_change_password_checks_current_password_and_revokes_other_sessions(self) -> None:
        user = server.authenticate_user("admin", TEST_INITIAL_PASSWORD)
        self.assertIsNotNone(user)
        current_session = server.create_auth_session(int(user["user_id"]))
        other_session = server.create_auth_session(int(user["user_id"]))
        server.change_user_password(int(user["user_id"]), TEST_INITIAL_PASSWORD, "new-password-8113", current_session)
        self.assertIsNone(server.authenticate_user("admin", TEST_INITIAL_PASSWORD))
        self.assertIsNotNone(server.authenticate_user("admin", "new-password-8113"))
        self.assertIsNotNone(server.auth_user_for_session(current_session))
        self.assertIsNone(server.auth_user_for_session(other_session))

    def test_change_password_rejects_wrong_current_password(self) -> None:
        user = server.authenticate_user("manager", TEST_INITIAL_PASSWORD)
        with self.assertRaises(PermissionError):
            server.change_user_password(int(user["user_id"]), "wrong", "new-password-8113", "")

    def test_recovery_code_resets_password_and_revokes_sessions(self) -> None:
        user = server.authenticate_user("worker", TEST_INITIAL_PASSWORD)
        session = server.create_auth_session(int(user["user_id"]))
        self.assertTrue(server.recover_user_password("worker", "local-recovery-code", "worker-new-password"))
        self.assertIsNone(server.auth_user_for_session(session))
        self.assertIsNotNone(server.authenticate_user("worker", "worker-new-password"))

    def test_recovery_rejects_invalid_code(self) -> None:
        with self.assertRaises(PermissionError):
            server.recover_user_password("worker", "wrong-code", "worker-new-password")

    def test_password_policy_rejects_short_password(self) -> None:
        with self.assertRaises(ValueError):
            server.validate_new_password("12345")


if __name__ == "__main__":
    unittest.main()
