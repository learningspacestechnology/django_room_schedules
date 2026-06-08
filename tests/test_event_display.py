from datetime import datetime, timezone

from django.test import TestCase

from room_schedules.models import Building, Event, Room


class EventDisplayTitleTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        building = Building.objects.create(name="Test Building")
        cls.room = Room.objects.create(name="Room 1", building=building)

    def _event(self, **kwargs):
        defaults = dict(
            name="Quarterly Strategy Review",
            room=self.room,
            organiser="Alice Smith",
            start_time=datetime(2026, 6, 5, 9, 0, tzinfo=timezone.utc),
            end_time=datetime(2026, 6, 5, 10, 0, tzinfo=timezone.utc),
        )
        defaults.update(kwargs)
        return Event(**defaults)

    def test_normal_event_shows_subject(self):
        event = self._event(sensitivity="normal")
        self.assertEqual(event.display_title, "Quarterly Strategy Review")

    def test_private_event_shows_organiser(self):
        event = self._event(sensitivity="private")
        self.assertEqual(event.display_title, "Alice Smith")

    def test_confidential_event_shows_organiser(self):
        event = self._event(sensitivity="confidential")
        self.assertEqual(event.display_title, "Alice Smith")

    def test_private_event_without_organiser_falls_back(self):
        event = self._event(sensitivity="private", organiser="")
        self.assertEqual(event.display_title, "Private booking")
