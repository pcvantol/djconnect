"""Exercise the registered views against a real local pair journal and fake API."""
import asyncio
import base64
import hashlib
import json
import sys
import unittest
import uuid
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
from types import SimpleNamespace

from tests import test_direct_rich_pair as fixtures
from custom_components.djconnect.native_pair_enrollment import KEY, NativePairEnrollment
from custom_components.djconnect.native_pair_enrollment_http import native_pair_enrollment_views
from custom_components.djconnect.surface_push_contract import SurfacePushError
from custom_components.djconnect.native_pair_retirement import NativePairRetirementJournal


class Body:
    def __init__(self, raw):
        self.raw = raw

    async def iter_chunked(self, size):
        for offset in range(0, len(self.raw), size):
            yield self.raw[offset:offset + size]


class NativePairEnrollmentTests(unittest.IsolatedAsyncioTestCase):
    settle = fixtures.DirectRichPairTests.settle
    asyncTearDown = fixtures.DirectRichPairTests.asyncTearDown

    async def asyncSetUp(self):
        self.temp = TemporaryDirectory()
        directory = Path(self.temp.name)
        self.persistence = fixtures.PersistenceService(
            directory / "pair.sqlite", fixtures.SQLitePersistenceProvider())
        await self.persistence.async_initialize()
        self.entry = SimpleNamespace(entry_id="synthetic-entry", disabled_by=None,
            state=SimpleNamespace(value="loaded"),
            data={"device_id": "djconnect-ios-ABCDEF123456", "client_type": "ios",
                  "device_token": "SYNTHETIC-ONLY-PAIR"},
            options={"ha_install_id": "synthetic-ha"})
        self.runtime = fixtures.Runtime()
        self.runtime.entry = self.entry
        self.runtime.device_token = self.entry.data["device_token"]
        self.runtime.pairing_device_id = self.entry.data["device_id"]
        self.runtime.surface_registration_retirement = fixtures.PairingRetirement()
        self.domain = {self.entry.entry_id: self.runtime, fixtures.PERSISTENCE_SERVICE_KEY: self.persistence}
        self.path = directory / "core.config_entries"
        self.hass = SimpleNamespace(is_stopping=False, data={"djconnect": self.domain},
            config_entries=SimpleNamespace(async_entries=lambda _: [self.entry]),
            async_create_task=asyncio.create_task, config=SimpleNamespace(path=lambda *_: self.path),
            async_add_executor_job=lambda fn, *args: asyncio.to_thread(fn, *args))
        self.headers = fixtures.Headers({"Authorization": "Bearer " + self.runtime.device_token,
            "X-DJConnect-Device-ID": self.runtime.pairing_device_id, "X-DJConnect-Client-Type": "ios"})
        self.save_credential()
        fixtures.schedule_pair_registration(self.hass, self.runtime)
        self.registration = self.runtime.surface_pair_registration
        await self.settle()
        self.calls = []
        self.consent = True
        self.challenge_reply = None
        self.lose_receipt = False
        self.corrupt_status = False
        self.saved_receipt = None
        transport = SimpleNamespace(origin="https://ha-dev.example.com", post_first_key=self.upstream,
                                    post_install_token=self.issue_token, post_bootstrap_proof=self.issue_proof)
        self.publications = []
        self.publisher = SimpleNamespace(origin="https://publisher.example.com", publish=self.publish)
        self.service = NativePairEnrollment(self.hass, transport, SimpleNamespace(capture=self.select),
                                            publisher=self.publisher)
        self.install_path = directory / "native-install"
        self.install_key = "synthetic-install-store"
        self.acknowledge_save = True
        store = SimpleNamespace(path=self.install_path, key=self.install_key, async_save=self.save_install)
        override = patch("custom_components.djconnect.native_pair_enrollment._install_store", return_value=store)
        override.start()
        self.addCleanup(override.stop)
        pair = fixtures.pair.capture_pair(self.hass, self.headers,
            device_id=self.runtime.pairing_device_id, client_type="ios")
        await self.save_install({**self.service.install_binding(pair), "install_token": "djci_synthetic",
                                 "credential_id": "credential"})
        self.domain[KEY] = self.service
        self.views = {getattr(view, "operation", "consent"): view
                      for view in native_pair_enrollment_views(self.hass)}
        self.assertEqual(await self.widget_consent(),
                         (200, {"contract_version": 1, "enabled": False, "revision": 0}))
        self.assertEqual((await self.widget_consent(enabled=True, expected_revision=0))[0], 200)

    def save_credential(self):
        self.path.write_text(json.dumps({"data": {"entries": [{
            "entry_id": self.entry.entry_id, "domain": "djconnect",
            "data": dict(self.entry.data), "options": dict(self.entry.options),
        }]}}))

    async def save_install(self, data):
        if self.acknowledge_save:
            self.install_path.write_text(json.dumps({"key": self.install_key, "version": 1, "data": data}))

    async def publish(self, action, body, *, guard, deadline):
        guard()
        self.publications.append((action, body))

    async def issue_proof(self, body, *, guard, deadline):
        guard()
        self.assertEqual(set(body), {"ha_install_id", "integration", "integration_version", "device_id", "client_type"})
        self.issued_identity = body
        self.calls.append("issue_proof")
        expires = datetime.fromtimestamp(self.service.wall() + 59, tz=UTC).isoformat()
        return SimpleNamespace(body={"ok": True, "bootstrap_proof": "synthetic-short-lived-proof",
                                    "expires_at": expires})

    async def issue_token(self, body, *, guard, deadline):
        guard()
        self.assertEqual(body["bootstrap_proof"], "synthetic-short-lived-proof")
        self.assertEqual({key: value for key, value in body.items() if key != "bootstrap_proof"}, self.issued_identity)
        self.assertEqual(body["ha_install_id"], "synthetic-ha")
        self.calls.append("issue_token")
        return SimpleNamespace(body={"success": True, "install_token": "djci_synthetic", "id": "credential"})

    async def use_fresh_pair(self):
        self.install_path.unlink()

    async def select(self, pair, *, channel):
        self.assertEqual(channel, "widgetkit")
        self.assertIs(pair.acknowledgement, self.registration.acknowledgement)
        return SimpleNamespace(current=lambda: self.consent, public_key_spki=b"synthetic-key",
            bindings={"pairing_generation": "opaque", "pair_binding": "a" * 64,
                      "owner_binding": "b" * 64, "device_binding": "c" * 64},
            sign=self.sign)

    def sign(self, statement):
        self.statement = statement
        return bytes(64)

    async def upstream(self, action, body, token, *, currentness, guard, deadline):
        guard()
        self.assertEqual(token, "djci_synthetic")
        self.calls.append(action)
        self.assertEqual(currentness["action"], action)
        self.assertEqual(currentness["install_credential_id"], "credential")
        self.assertEqual(currentness["operation_id"], body["operation_id"])
        encoded = json.dumps(body, separators=(",", ":"), sort_keys=True).encode()
        self.assertEqual(currentness["request_sha256"], hashlib.sha256(encoded).hexdigest())
        self.assertLessEqual(currentness["expires_at_ms"] - currentness["issued_at_ms"], 10_000)
        if action == "status":
            self.assertLessEqual(currentness["expires_at_ms"], body["status_nonce_expires_at_ms"])
        if action == "challenge":
            self.assertIsNone(currentness["operation_expires_at_ms"])
            reply = {"contract_version": 1, "operation_id": body["operation_id"],
                     "api_audience": "djc-native-push-ha-dev/1", "api_installation_id": "api-install",
                     "install_credential_id": "credential", "challenge_id": "challenge",
                     "challenge_nonce": "A" * 43, "expected_key_revision": 0,
                     "expires_at_ms": int(self.service.wall() * 1000) + 60_000}
            self.challenge_reply = reply
        elif action == "status/challenge":
            receipt = self.saved_receipt
            reply = {**body, "api_audience": self.challenge_reply["api_audience"],
                     **{key: receipt[key] for key in ("install_credential_id", "pairing_generation",
                         "core_key_thumbprint", "expires_at_ms")},
                     "status_nonce_id": "status-challenge", "status_nonce": "B" * 42 + "A",
                     "status_nonce_expires_at_ms": int(self.service.wall() * 1000) + 10_000}
            if self.corrupt_status:
                reply["pairing_generation"] = "foreign"
        elif action == "status":
            self.assertEqual(body["status_nonce_id"], "status-challenge")
            self.assertIn(b"djc-native-first-key-status/1", self.statement)
            reply = self.saved_receipt
        else:
            self.assertEqual(len(base64.b64decode(body["apple_proof"]["proof_b64"])), 16_384)
            reply = {key: body[key] for key in ("contract_version", "operation_id", "api_installation_id",
                      "install_credential_id", "expires_at_ms", "pairing_generation", "core_key_thumbprint")}
            reply.update(registry_generation="registered", key_revision=1, state="registered",
                         transcript_sha256=hashlib.sha256(self.statement).hexdigest())
            self.saved_receipt = reply
            if self.lose_receipt:
                raise SurfacePushError("surface_issuer_outcome_unknown", 502)
        return SimpleNamespace(body=reply)

    async def post(self, operation, **extra):
        view = self.views[operation]
        raw = json.dumps({"contract_version": 1, "device_id": self.runtime.pairing_device_id,
                          "client_type": "ios", **extra}).encode()
        headers = fixtures.Headers({**self.headers, "Content-Type": "application/json"})
        response = await view.post(SimpleNamespace(raw_path=view.url, headers=headers,
            content=Body(raw), content_length=len(raw)))
        return response.status, json.loads(response.body)

    async def widget_consent(self, *, enabled=None, expected_revision=None, operation_id=None, headers=None):
        view = self.views["consent"]
        headers = self.headers if headers is None else headers
        if enabled is None:
            response = await view.get(SimpleNamespace(raw_path=view.url, headers=headers, can_read_body=False))
        else:
            raw = json.dumps({"contract_version": 1, "enabled": enabled, "expected_revision": expected_revision,
                              "operation_id": operation_id or str(uuid.uuid4())}).encode()
            response = await view.post(SimpleNamespace(raw_path=view.url,
                headers=fixtures.Headers({**headers, "Content-Type": "application/json"}),
                content=Body(raw), content_length=len(raw)))
        return response.status, json.loads(response.body)

    async def test_widget_consent_replay_and_stale_enable_cannot_undo_withdrawal(self):
        status, challenge = await self.post("challenge")
        self.assertEqual(status, 200, challenge)
        operation = str(uuid.uuid4())
        result = await self.widget_consent(enabled=False, expected_revision=1, operation_id=operation)
        self.assertEqual(result, (200, {"contract_version": 1, "enabled": False,
                                        "revision": 2, "operation_id": operation}))
        self.assertEqual(await self.widget_consent(enabled=False, expected_revision=1, operation_id=operation), result)
        self.assertEqual((await self.widget_consent(enabled=True, expected_revision=1, operation_id=operation))[0], 409)
        self.assertEqual((await self.widget_consent(enabled=True, expected_revision=1))[0], 409)
        self.assertEqual(await self.widget_consent(),
                         (200, {"contract_version": 1, "enabled": False, "revision": 2}))
        self.assertEqual((await self.post("register", operation_id=challenge["operation_id"],
                                          apple_proof=self.proof()))[0], 403)
        self.assertEqual(self.calls, ["challenge"])

    async def test_widget_consent_cannot_be_read_by_another_device(self):
        foreign = fixtures.Headers({**self.headers, "X-DJConnect-Device-ID": "djconnect-ios-FOREIGN12345"})
        self.assertEqual((await self.widget_consent(headers=foreign))[0], 401)
        self.assertEqual(await self.widget_consent(),
                         (200, {"contract_version": 1, "enabled": True, "revision": 1}))

    async def test_widget_consent_is_durable_and_a_new_pair_starts_off(self):
        self.service = NativePairEnrollment(self.hass, self.service.transport, self.service.selection,
                                            publisher=self.publisher)
        self.domain[KEY] = self.service
        self.assertEqual(await self.widget_consent(),
                         (200, {"contract_version": 1, "enabled": True, "revision": 1}))

        old_headers = self.headers
        self.registration.retire()
        await self.settle()
        new_token = "SYNTHETIC-NEW-PAIR"
        self.entry.data = {**self.entry.data, "device_token": new_token}
        self.runtime.device_token = new_token
        self.runtime.surface_registration_retirement = fixtures.PairingRetirement()
        self.save_credential()
        fixtures.schedule_pair_registration(self.hass, self.runtime)
        self.registration = self.runtime.surface_pair_registration
        await self.settle()
        self.headers = fixtures.Headers({**self.headers, "Authorization": "Bearer " + new_token})
        self.assertEqual((await self.widget_consent(headers=old_headers))[0], 401)
        self.assertEqual(await self.widget_consent(),
                         (200, {"contract_version": 1, "enabled": False, "revision": 0}))

    async def test_widget_withdrawal_blocks_status_of_a_registered_key(self):
        status, challenge = await self.post("challenge")
        self.assertEqual(status, 200)
        operation = {"operation_id": challenge["operation_id"]}
        self.assertEqual((await self.post("register", **operation, apple_proof=self.proof()))[0], 200)
        self.assertEqual((await self.widget_consent(enabled=False, expected_revision=1))[0], 200)
        self.assertEqual((await self.post("status", **operation))[0], 403)
        self.assertEqual(self.calls, ["challenge", "register"])

    def proof(self):
        return {"kind": "attestation", "key_id_b64": base64.b64encode(bytes(32)).decode(),
                "proof_b64": base64.b64encode(bytes(16_384)).decode()}

    async def test_paired_challenge_register_and_replay(self):
        status, challenge = await self.post("challenge")
        self.assertEqual(status, 200, challenge)
        data = {"operation_id": challenge["operation_id"], "apple_proof": self.proof()}
        status, receipt = await self.post("register", **data)
        self.assertEqual(status, 200, receipt)
        self.assertEqual(base64.b64decode(challenge["client_data_hash_b64"]),
                         hashlib.sha256(self.statement).digest())
        self.assertEqual((await self.post("register", **data))[0], 409)
        self.assertEqual(self.calls, ["challenge", "register"])

    async def test_no_consent_or_disk_ack_means_no_api_call(self):
        self.consent = False
        self.assertEqual((await self.post("challenge"))[0], 403)
        self.consent = True
        saved = json.loads(self.path.read_text())
        saved["data"]["entries"][0]["data"]["device_token"] = "STALE-PAIR"
        self.path.write_text(json.dumps(saved))
        self.assertEqual((await self.post("challenge"))[0], 503)
        self.path.unlink()
        self.assertEqual((await self.post("challenge"))[0], 503)
        self.assertEqual(self.calls, [])

    async def test_registration_refuses_an_unregistered_worker_receipt(self):
        upstream = self.service.transport.post_first_key

        async def wrong_state(action, *args, **kwargs):
            reply = await upstream(action, *args, **kwargs)
            if action == "register":
                reply.body = {**reply.body, "state": "pending"}
            return reply

        self.service.transport.post_first_key = wrong_state
        status, challenge = await self.post("challenge")
        self.assertEqual(status, 200, challenge)
        self.assertEqual(await self.post("register", operation_id=challenge["operation_id"],
                                         apple_proof=self.proof()),
                         (502, {"error": "native_pair_receipt_invalid"}))
        self.assertEqual((await self.post("status", operation_id=challenge["operation_id"]))[0], 200)

    async def test_consent_revoked_after_challenge_blocks_register(self):
        status, challenge = await self.post("challenge")
        self.assertEqual(status, 200, challenge)
        self.consent = False
        self.assertEqual((await self.post("register", operation_id=challenge["operation_id"],
                                          apple_proof=self.proof()))[0], 403)
        self.assertEqual(self.calls, ["challenge"])

    async def test_fresh_pair_bootstraps_once_and_waits_for_channel_consent(self):
        await self.use_fresh_pair()
        self.consent = False
        self.assertEqual(await self.post("bootstrap"), (200, {"contract_version": 1, "ready": True}))
        self.assertEqual((await self.post("bootstrap"))[0], 200)
        self.assertEqual((await self.post("challenge"))[0], 403)
        self.assertEqual(self.calls, ["issue_proof", "issue_token"])
        self.consent = True
        self.assertEqual((await self.post("challenge"))[0], 200)
        self.assertEqual(self.calls, ["issue_proof", "issue_token", "challenge"])

    async def test_bootstrap_rechecks_original_disk_pair_before_token_exchange(self):
        await self.use_fresh_pair()

        async def replace_disk_pair(body, *, guard, deadline):
            reply = await self.issue_proof(body, guard=guard, deadline=deadline)
            saved = json.loads(self.path.read_text())
            saved["data"]["entries"][0]["data"]["device_token"] = "replaced-on-disk"
            self.path.write_text(json.dumps(saved))
            return reply

        self.service.transport.post_bootstrap_proof = replace_disk_pair
        self.assertEqual((await self.post("bootstrap"))[0], 503)
        self.assertFalse(self.install_path.exists())
        self.assertEqual(self.calls, ["issue_proof"])

    async def test_failed_install_store_write_never_unlocks_challenge(self):
        await self.use_fresh_pair()
        self.acknowledge_save = False
        self.assertEqual((await self.post("bootstrap"))[0], 503)
        self.assertEqual((await self.post("challenge"))[0], 503)
        self.assertEqual(self.calls, ["issue_proof", "issue_token"])

    async def test_replaced_install_credential_cannot_use_original_challenge(self):
        await self.use_fresh_pair()
        self.assertEqual((await self.post("bootstrap"))[0], 200)
        status, challenge = await self.post("challenge")
        self.assertEqual(status, 200, challenge)
        saved = json.loads(self.install_path.read_text())
        saved["data"]["install_token"] = "djci_replaced"
        self.install_path.write_text(json.dumps(saved))
        self.assertEqual((await self.post("register", operation_id=challenge["operation_id"],
                                          apple_proof=self.proof()))[0], 403)
        self.assertEqual(self.calls, ["issue_proof", "issue_token", "challenge"])

    async def test_lost_register_response_recovers_only_original_signed_receipt(self):
        self.lose_receipt = True
        status, challenge = await self.post("challenge")
        self.assertEqual(status, 200, challenge)
        identity = {"operation_id": challenge["operation_id"]}
        self.assertEqual((await self.post("register", **identity, apple_proof=self.proof()))[0], 502)
        self.assertEqual((await self.post("register", **identity, apple_proof=self.proof()))[0], 409)
        self.corrupt_status = True
        self.assertEqual((await self.post("status", **identity))[0], 502)
        self.corrupt_status = False
        self.assertEqual(await self.post("status", **identity), (200, self.saved_receipt))
        self.assertEqual(await self.post("status", **identity), (200, self.saved_receipt))
        self.assertEqual(self.calls, ["challenge", "register", "status/challenge",
                                     "status/challenge", "status", "status/challenge", "status"])

    async def test_pair_retirement_keeps_exact_remote_event_pending_until_acknowledged(self):
        status, challenge = await self.post("challenge")
        self.assertEqual(status, 200, challenge)
        journal = NativePairRetirementJournal(self.persistence)
        origin = self.service.transport.origin
        self.assertEqual(await journal.pending(origin), [])
        self.registration.retire()
        await self.settle()
        [event] = await journal.pending(origin)
        self.assertEqual(event.body()["pair_binding"], challenge["pair_binding"])
        self.assertEqual(event.body()["install_credential_id"], "credential")
        self.assertEqual(event.event_id, challenge["operation_id"])
        self.assertEqual(await journal.pending("https://other.example.com"), [])
        self.assertFalse(await journal.acknowledge(replace(event, origin="https://other.example.com")))
        reopened = fixtures.PersistenceService(
            Path(self.temp.name) / "pair.sqlite", fixtures.SQLitePersistenceProvider())
        await reopened.async_initialize()
        self.addAsyncCleanup(reopened.async_close)
        after_restart = NativePairRetirementJournal(reopened)
        [retried] = await after_restart.pending(origin)
        self.assertEqual(retried, event)
        good_ack = {"contract_version": 1, "api_audience": "djc-native-push-ha-dev/1",
                    "event_id": event.event_id, "pair_binding": event.body()["pair_binding"],
                    "event_sha256": hashlib.sha256(event.original.encode()).hexdigest(), "state": "retired"}
        deliveries = []

        async def deliver(body, *, guard, deadline):
            self.assertEqual(body, event.body())
            deliveries.append(body)
            ack = {**good_ack, "event_sha256": "0" * 64} if len(deliveries) == 1 else good_ack
            return SimpleNamespace(status=200, body=ack)

        transport = SimpleNamespace(origin=origin, post_retirement=deliver)
        with self.assertRaisesRegex(SurfacePushError, "native_retirement_ack_invalid"):
            await after_restart.deliver(transport, guard=lambda: None, deadline=10)
        self.assertEqual(await after_restart.pending(origin), [event])
        self.assertEqual(await after_restart.deliver(transport, guard=lambda: None, deadline=10), 1)
        self.assertEqual(await journal.pending(origin), [])

    async def test_publisher_binds_and_publishes_before_challenge(self):
        await self.use_fresh_pair()
        self.assertEqual((await self.post("bootstrap"))[0], 200)
        self.assertEqual(self.publications, [("bind", {
            "contract_version": 1, "ha_install_id": "synthetic-ha",
            "device_id": self.runtime.pairing_device_id,
        })])
        status, challenge = await self.post("challenge")
        self.assertEqual(status, 200, challenge)
        [_, (action, publication)] = self.publications
        self.assertEqual(action, "operation")
        self.assertEqual(publication["operation_id"], challenge["operation_id"])
        self.assertEqual(publication["consent_revision"], 1)
        self.assertNotIn("api_audience", publication)
        self.assertNotIn("event_id", publication)
        self.assertNotIn("install_token", publication)

    async def test_failed_withdrawal_retries_without_disabling_fresh_revision(self):
        self.assertEqual((await self.post("challenge"))[0], 200)
        self.assertEqual((await self.widget_consent(enabled=False, expected_revision=1))[0], 200)
        self.assertEqual((await self.widget_consent(enabled=True, expected_revision=2))[0], 200)
        self.assertEqual((await self.post("challenge"))[0], 200)
        journal = NativePairRetirementJournal(self.persistence)
        origin = self.service.transport.origin

        async def unavailable(action, body, *, guard, deadline):
            raise SurfacePushError("native_publisher_ack_invalid", 502)

        with self.assertRaisesRegex(SurfacePushError, "native_publisher_ack_invalid"):
            await journal.deliver_withdrawals(
                SimpleNamespace(origin=self.publisher.origin, publish=unavailable),
                origin, guard=lambda: None, deadline=10)
        await journal.deliver_withdrawals(self.publisher, origin, guard=lambda: None, deadline=10)
        await journal.deliver_withdrawals(self.publisher, origin, guard=lambda: None, deadline=10)
        withdrawals = [body for action, body in self.publications if action == "withdraw"]
        self.assertEqual(withdrawals, [{
            "contract_version": 1, "pair_binding": "a" * 64, "consent_revision": 1,
        }])

    async def test_persisted_consent_revision_is_checked_in_the_stage_transaction(self):
        from custom_components.djconnect.native_widget_consent import write_widget_consent

        stage = NativePairRetirementJournal.stage

        async def withdraw_before_stage(journal, pair, *args):
            await write_widget_consent(pair, enabled=False, operation_id=str(uuid.uuid4()),
                                       expected_revision=1)
            await stage(journal, pair, *args)

        with patch.object(NativePairRetirementJournal, "stage", withdraw_before_stage):
            self.assertEqual(await self.post("challenge"),
                             (403, {"error": "native_widget_consent_changed"}))
        self.assertEqual(self.calls, [])
        rows = await self.persistence.async_in_transaction(lambda tx:
            tx.fetchall("SELECT consent_revision FROM djconnect_native_pair_retirements"))
        self.assertEqual(rows, [])

    async def test_pair_retired_after_durable_stage_never_reaches_api(self):
        stage = NativePairRetirementJournal.stage

        async def retire_after_stage(journal, *args):
            await stage(journal, *args)
            self.registration.retire()
            await self.settle()

        with patch.object(NativePairRetirementJournal, "stage", retire_after_stage):
            self.assertEqual((await self.post("challenge"))[0], 403)
        self.assertEqual(self.calls, [])
        pending = await NativePairRetirementJournal(self.persistence).pending(self.service.transport.origin)
        self.assertEqual(len(pending), 1)

    async def test_selected_service_retries_on_ha_schedule_until_confirmed(self):
        self.assertEqual((await self.post("challenge"))[0], 200)
        self.registration.retire()
        await self.settle()
        scheduler = []
        stopped = []

        def schedule(hass, callback, interval):
            self.assertIs(hass, self.hass)
            self.assertEqual(interval.total_seconds(), 30)
            scheduler.append(callback)
            return lambda: stopped.append(True)

        module = SimpleNamespace(async_track_time_interval=schedule)
        with patch.dict(sys.modules, {"homeassistant.helpers.event": module}):
            self.service.start_retirement_delivery()
            self.service.start_retirement_delivery()
        self.assertEqual(len(scheduler), 1)
        journal = NativePairRetirementJournal(self.persistence)
        [event] = await journal.pending(self.service.transport.origin)
        attempts = []

        async def deliver(body, *, guard, deadline):
            guard()
            attempts.append(body)
            if len(attempts) == 1:
                raise SurfacePushError("api_unavailable", 503)
            return SimpleNamespace(status=200, body={"contract_version": 1, "state": "retired",
                "api_audience": body["api_audience"], "event_id": event.event_id,
                "pair_binding": body["pair_binding"],
                "event_sha256": hashlib.sha256(event.original.encode()).hexdigest()})

        self.service.transport.post_retirement = deliver
        await scheduler[0](None)
        self.assertEqual(await journal.pending(self.service.transport.origin), [event])
        await scheduler[0](None)
        self.assertEqual(attempts, [event.body(), event.body()])
        self.assertEqual(await journal.pending(self.service.transport.origin), [])
        self.service.stop_retirement_delivery()
        self.assertEqual(stopped, [True])
        await scheduler[0](None)
        self.assertEqual(len(attempts), 2)

    async def test_apple_can_recover_lost_core_response_after_successful_register(self):
        status, challenge = await self.post("challenge")
        self.assertEqual(status, 200, challenge)
        identity = {"operation_id": challenge["operation_id"]}
        self.assertEqual((await self.post("register", **identity, apple_proof=self.proof()))[0], 200)
        self.assertEqual(await self.post("status", **identity), (200, self.saved_receipt))
        self.assertEqual(self.calls, ["challenge", "register", "status/challenge", "status"])
        self.registration.retire()
        await self.settle()
        self.assertEqual((await self.post("status", **identity))[0], 503)
        self.assertEqual(len(self.calls), 4)
