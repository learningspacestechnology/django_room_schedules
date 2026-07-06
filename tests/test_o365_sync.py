from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from room_schedules.models import Building, O365Room, Room
from room_schedules.tasks import sync_o365_rooms


def _tenant_room(email, name=None, building=""):
    return {
        "email": email,
        "name": name or email,
        "building": building,
        "floor": None,
        "capacity": None,
    }


class SyncMissingRoomTests(TestCase):
    """`sync_o365_rooms` only keeps a vanished mailbox when it still backs a
    real imported Room; unimported ones are deleted as stale inventory."""

    @classmethod
    def setUpTestData(cls):
        cls.building = Building.objects.create(name="Test Building")

    def _run_sync(self, tenant_rooms):
        async def fake_filter(rooms, **kwargs):
            # Treat every returned tenant room as calendar-accessible.
            return list(rooms), []

        with patch("room_schedules.tasks.list_tenant_rooms", return_value=tenant_rooms), \
             patch("room_schedules.tasks.filter_accessible_rooms", side_effect=fake_filter):
            return sync_o365_rooms()

    def test_missing_imported_room_is_flagged_and_kept(self):
        O365Room.objects.create(email="imported@x.com", name="Imported")
        Room.objects.create(
            name="Imported", building=self.building,
            o365_calendar_email="imported@x.com",
        )

        # Tenant no longer returns imported@x.com.
        self._run_sync([_tenant_room("present@x.com")])

        room = O365Room.objects.get(email="imported@x.com")
        self.assertTrue(room.missing_from_tenant)

    def test_missing_never_imported_room_is_deleted(self):
        O365Room.objects.create(email="orphan@x.com", name="Orphan")

        self._run_sync([_tenant_room("present@x.com")])

        self.assertFalse(O365Room.objects.filter(email="orphan@x.com").exists())

    def test_deleting_room_lets_missing_entry_be_cleaned_up(self):
        # A mailbox that was imported, then went missing (flagged), then had its
        # Room deleted, is dropped on the next sync.
        O365Room.objects.create(
            email="gone@x.com", name="Gone", missing_from_tenant=True,
        )
        # No matching Room exists (operator deleted it).

        self._run_sync([_tenant_room("present@x.com")])

        self.assertFalse(O365Room.objects.filter(email="gone@x.com").exists())

    def test_present_room_is_not_flagged(self):
        O365Room.objects.create(
            email="present@x.com", name="Present", missing_from_tenant=True,
        )

        self._run_sync([_tenant_room("present@x.com")])

        room = O365Room.objects.get(email="present@x.com")
        self.assertFalse(room.missing_from_tenant)


class UnassignedViewMissingSectionTests(TestCase):
    """The "Missing from tenant" section only lists rooms that currently back a
    real Room, so deleting the Room removes it immediately (before any sync)."""

    @classmethod
    def setUpTestData(cls):
        cls.building = Building.objects.create(name="Test Building")
        cls.admin = get_user_model().objects.create_superuser(
            username="admin", email="admin@x.com", password="pw",
        )

    def _missing_emails(self):
        self.client.force_login(self.admin)
        resp = self.client.get(reverse("admin:room_schedules_o365_unassigned"))
        self.assertEqual(resp.status_code, 200)
        return {r.email for r in resp.context["missing_rooms"]}

    def test_only_imported_missing_rooms_are_shown(self):
        O365Room.objects.create(
            email="imported@x.com", name="Imported", missing_from_tenant=True,
        )
        Room.objects.create(
            name="Imported", building=self.building,
            o365_calendar_email="imported@x.com",
        )
        O365Room.objects.create(
            email="orphan@x.com", name="Orphan", missing_from_tenant=True,
        )

        self.assertEqual(self._missing_emails(), {"imported@x.com"})

    def test_deleting_room_hides_missing_entry(self):
        O365Room.objects.create(
            email="imported@x.com", name="Imported", missing_from_tenant=True,
        )
        room = Room.objects.create(
            name="Imported", building=self.building,
            o365_calendar_email="imported@x.com",
        )
        self.assertEqual(self._missing_emails(), {"imported@x.com"})

        room.delete()
        self.assertEqual(self._missing_emails(), set())
