"""The HA-dev machine credential must not confer widget owner authority."""

import asyncio
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest

from tests import test_surface_widget_adoption as widget_fixture
from custom_components.djconnect.surface_push_contract import SurfacePushError
from custom_components.djconnect.surface_widget_private_transport import (
    WidgetAccessCustody,
    load_widget_access_file,
)


class WidgetAccessFileTests(unittest.TestCase):
    def test_reads_only_private_regular_file_with_closed_fields(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / "machine"
            record = {"client_id": "test-id", "client_secret": "test-secret", "expires_at_ms": 2000}
            path.write_text(json.dumps(record), encoding="utf-8")
            path.chmod(0o600)
            self.assertEqual(load_widget_access_file(str(path)), ("test-id", "test-secret", 2000))
            link = Path(root) / "alias"
            link.symlink_to(path)
            with self.assertRaises(SurfacePushError):
                load_widget_access_file(str(link))
            path.chmod(0o644)
            with self.assertRaises(SurfacePushError):
                load_widget_access_file(str(path))
            path.chmod(0o600)
            for bad in (json.dumps({**record, "origin": "https://other.invalid"}),
                        '{"client_id":"a","client_id":"b","client_secret":"c","expires_at_ms":2000}'):
                with self.subTest(case=bad):
                    path.write_text(bad, encoding="utf-8")
                    with self.assertRaises(SurfacePushError):
                        load_widget_access_file(str(path))

    def test_expires_on_monotonic_deadline_and_cannot_be_rebound(self):
        clocks = SimpleNamespace(wall=1000, mono=10)
        custody = WidgetAccessCustody(wall_ms=lambda: clocks.wall, monotonic=lambda: clocks.mono)
        transport = custody.bind("test-id", "test-secret", 2000)
        origin = "https://widget-ha-dev.djconnect.dev"
        transport.validate_origin(origin)
        with self.assertRaises(SurfacePushError):
            transport.validate_origin("https://other.invalid")
        clocks.mono = 11
        with self.assertRaises(SurfacePushError):
            transport.validate_origin(origin)
        clocks.mono = 10
        with self.assertRaises(SurfacePushError):
            transport.validate_origin(origin)
        with self.assertRaises(SurfacePushError):
            custody.bind("another-id", "another-secret", 3000)


class WidgetServiceMachineAccessTests(unittest.IsolatedAsyncioTestCase):
    async def test_machine_access_does_not_admit_owner_and_closes_on_stop(self):
        fixture = widget_fixture.WidgetAdoptionTests()
        await fixture.asyncSetUp()
        self.addAsyncCleanup(fixture.asyncTearDown)
        service = fixture.service
        service.hass.async_add_executor_job = asyncio.to_thread
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / "machine"
            path.write_text(json.dumps({
                "client_id": "test-id", "client_secret": "test-secret",
                "expires_at_ms": 8_000_000_000_000,
            }), encoding="utf-8")
            path.chmod(0o600)
            await service.load_private_widget_access(str(path))
        with self.assertRaises(SurfacePushError):
            service.begin_enrolled_widget_adoption(object(), "", {}, {})
        self.assertEqual(service._purposes, {})
        self.assertIsNone(service._widget_lifecycle)
        transport = service._widget_transport
        self.assertIsNotNone(transport)
        # Neither a paired request nor the machine credential supplies an owner.
        fixture.paired_valid = False
        with self.assertRaises(SurfacePushError):
            service.begin_enrolled_widget_adoption(fixture.owner, "", fixture.identity, fixture.headers)
        fixture.paired_valid = True
        handle = service.begin_enrolled_widget_adoption(fixture.owner, "", fixture.identity, fixture.headers)
        self.assertIs(handle.lifecycle.transport, transport)
        self.assertIs(handle.lifecycle.owner, fixture.owner)
        self.assertEqual(service._purposes, {})
        with self.assertRaises(SurfacePushError):
            service.begin_enrolled_widget_adoption(
                widget_fixture.SyntheticWidgetOwner(), "", fixture.identity, fixture.headers,
            )
        await service.close()
        with self.assertRaises(SurfacePushError):
            transport.validate_origin("https://widget-ha-dev.djconnect.dev")
