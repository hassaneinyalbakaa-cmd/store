import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from backend.app.admin_recovery import (
    RESET_ACTION,
    apply_admin_password_reset,
    recover_admin_on_startup,
)


class AdminRecoveryTests(unittest.IsolatedAsyncioTestCase):
    def make_db(self, *, completed=False, active=True, role="admin", exists=True):
        user = SimpleNamespace(
            id=1,
            username="admin",
            display_name="Administrator",
            is_active=active,
            role=SimpleNamespace(name=role),
            password_hash="unchanged-hash",
        )
        found = MagicMock()
        found.scalar_one_or_none.return_value = user if exists else None
        marker = MagicMock()
        marker.scalar_one_or_none.return_value = 7 if completed else None
        db = MagicMock()
        db.execute = AsyncMock(side_effect=[found, marker, MagicMock()])
        return db, user

    async def test_reset_updates_only_admin_and_revokes_sessions(self):
        db, user = self.make_db()
        request_id = str(uuid4())
        with patch(
            "backend.app.admin_recovery.hash_password", return_value="new-hash"
        ), patch("backend.app.admin_recovery.add_audit_log") as audit:
            changed = await apply_admin_password_reset(
                db, request_id=request_id, password="test-only-long-password"
            )
        self.assertTrue(changed)
        self.assertEqual(user.password_hash, "new-hash")
        self.assertIn("FOR UPDATE", str(db.execute.call_args_list[0].args[0]))
        deletion = db.execute.call_args_list[2].args[0]
        self.assertEqual(deletion.table.name, "user_sessions")
        self.assertIn(user.id, deletion.compile().params.values())
        self.assertEqual(audit.call_args.kwargs["document_number"], request_id)
        self.assertEqual(audit.call_args.kwargs["action"], RESET_ACTION)
        db.commit.assert_not_called()

    async def test_completed_request_preserves_later_password_without_secret(self):
        db, user = self.make_db(completed=True)
        with patch("backend.app.admin_recovery.hash_password") as hash_password:
            changed = await apply_admin_password_reset(
                db, request_id=str(uuid4()), password=None
            )
        self.assertFalse(changed)
        self.assertEqual(user.password_hash, "unchanged-hash")
        hash_password.assert_not_called()
        db.add.assert_not_called()
        self.assertEqual(db.execute.await_count, 2)

    async def test_invalid_request_id_never_queries_database(self):
        db, _ = self.make_db()
        with self.assertRaisesRegex(RuntimeError, "valid UUID"):
            await apply_admin_password_reset(
                db, request_id="invalid", password="test-only-long-password"
            )
        db.execute.assert_not_awaited()

    async def test_invalid_password_never_changes_account(self):
        for password in (None, "", "short", " " * 15):
            with self.subTest(password_present=bool(password)):
                db, user = self.make_db()
                with self.assertRaisesRegex(RuntimeError, "12 characters"):
                    await apply_admin_password_reset(
                        db, request_id=str(uuid4()), password=password
                    )
                self.assertEqual(user.password_hash, "unchanged-hash")
                self.assertEqual(db.execute.await_count, 2)
                db.add.assert_not_called()

    async def test_missing_disabled_or_nonadmin_account_is_not_changed(self):
        for options in ({"exists": False}, {"active": False}, {"role": "viewer"}):
            with self.subTest(options=options):
                db, user = self.make_db(**options)
                with self.assertRaisesRegex(RuntimeError, "active admin"):
                    await apply_admin_password_reset(
                        db,
                        request_id=str(uuid4()),
                        password="test-only-long-password",
                    )
                self.assertEqual(user.password_hash, "unchanged-hash")
                self.assertEqual(db.execute.await_count, 1)

    async def test_startup_is_disabled_in_development_or_without_request(self):
        for environment, request_id in (
            ("development", str(uuid4())),
            ("production", None),
        ):
            with patch("backend.app.admin_recovery.SessionLocal") as factory:
                await recover_admin_on_startup(
                    SimpleNamespace(
                        environment=environment, admin_reset_request_id=request_id
                    )
                )
                factory.assert_not_called()

    async def test_startup_uses_atomic_transaction(self):
        db, _ = self.make_db()
        transaction = MagicMock()
        transaction.__aenter__ = AsyncMock()
        transaction.__aexit__ = AsyncMock(return_value=False)
        db.begin.return_value = transaction
        context = MagicMock()
        context.__aenter__ = AsyncMock(return_value=db)
        context.__aexit__ = AsyncMock(return_value=False)
        secret = MagicMock()
        secret.get_secret_value.return_value = "test-only-long-password"
        settings = SimpleNamespace(
            environment="production",
            admin_reset_request_id=str(uuid4()),
            admin_reset_password=secret,
        )
        with patch(
            "backend.app.admin_recovery.SessionLocal", return_value=context
        ), patch(
            "backend.app.admin_recovery.apply_admin_password_reset",
            new_callable=AsyncMock,
            side_effect=RuntimeError("test transaction failure"),
        ):
            with self.assertRaisesRegex(RuntimeError, "test transaction failure"):
                await recover_admin_on_startup(settings)
        self.assertIs(transaction.__aexit__.call_args.args[0], RuntimeError)


if __name__ == "__main__":
    unittest.main()
