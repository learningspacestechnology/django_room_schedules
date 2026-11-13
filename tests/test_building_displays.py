import datetime
from unittest import mock

from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from room_schedules.models import Building, Event, IpAddress, Room, RoomGroup

DEVICE_IP = "10.0.61.1"


def local(*args):
    return timezone.make_aware(datetime.datetime(*args))


# Friday afternoon. The grid runs 08:00–18:00 (the defaults).
NOW = local(2026, 11, 13, 14, 0)


class BuildingDisplayTests(TestCase):
    """The building grid and foyer: which bookings each shows, and where."""

    @classmethod
    def setUpTestData(cls):
        cls.building = Building.objects.create(name="Riverside Library")
        cls.room = Room.objects.create(name="Room A", building=cls.building)
        cls.empty_room = Room.objects.create(name="Room B", building=cls.building)
        IpAddress.objects.create(ip_address=DEVICE_IP, building=cls.building)

        bookings = {
            "Yesterday Meeting": ((2026, 11, 12, 10, 0), (2026, 11, 12, 11, 0)),
            "Early Breakfast": ((2026, 11, 13, 6, 0), (2026, 11, 13, 7, 0)),
            "Early Start": ((2026, 11, 13, 7, 30), (2026, 11, 13, 9, 0)),
            "Morning Lecture": ((2026, 11, 13, 10, 0), (2026, 11, 13, 11, 0)),
            "Current Workshop": ((2026, 11, 13, 13, 30), (2026, 11, 13, 15, 0)),
            "Late Seminar": ((2026, 11, 13, 17, 0), (2026, 11, 13, 19, 0)),
            "Evening Class": ((2026, 11, 13, 19, 0), (2026, 11, 13, 20, 0)),
            "Tomorrow Talk": ((2026, 11, 14, 10, 0), (2026, 11, 14, 11, 0)),
        }
        for name, (start, end) in bookings.items():
            Event.objects.create(
                name=name, organiser="Organiser", room=cls.room,
                start_time=local(*start), end_time=local(*end),
            )

    def setUp(self):
        self.client = Client(REMOTE_ADDR=DEVICE_IP)
        patcher = mock.patch("django.utils.timezone.now", return_value=NOW)
        patcher.start()
        self.addCleanup(patcher.stop)

    def grid(self):
        return self.client.get(reverse("room_schedule/building", args=[self.building.pk]))

    def foyer(self):
        return self.client.get(reverse("room_schedule/building_foyer", args=[self.building.pk]))

    @staticmethod
    def placed(start, end):
        return "--edgel-start-minutes:{}; --edgel-end-minutes:{};".format(start, end)

    # ── Grid ──

    def test_grid_keeps_bookings_that_have_finished_today(self):
        response = self.grid()
        self.assertContains(response, "Morning Lecture")
        self.assertContains(response, self.placed(120, 180))

    def test_grid_leaves_out_bookings_wholly_outside_its_hours(self):
        response = self.grid()
        for name in ("Early Breakfast", "Evening Class"):
            with self.subTest(name=name):
                self.assertNotContains(response, name)

    def test_grid_cuts_off_bookings_crossing_its_edges(self):
        response = self.grid()
        self.assertContains(response, self.placed(0, 60))     # Early Start, 07:30–09:00
        self.assertContains(response, self.placed(540, 600))  # Late Seminar, 17:00–19:00

    def test_grid_shows_only_today(self):
        response = self.grid()
        for name in ("Yesterday Meeting", "Tomorrow Talk"):
            with self.subTest(name=name):
                self.assertNotContains(response, name)

    def test_grid_hours_can_run_to_midnight(self):
        Building.objects.filter(pk=self.building.pk).update(grid_end_hour=24)
        response = self.grid()
        self.assertContains(response, "Evening Class")
        self.assertContains(response, self.placed(660, 720))

    def test_after_midnight_the_grid_still_shows_the_evening_before(self):
        # Display days turn over at HOUR_BREAK_POINT (04:00), not midnight.
        with mock.patch("django.utils.timezone.now", return_value=local(2026, 11, 14, 1, 0)):
            response = self.grid()
        self.assertContains(response, "Morning Lecture")
        self.assertNotContains(response, "Tomorrow Talk")

    def test_room_group_grid_uses_the_same_rules(self):
        group = RoomGroup.objects.create(name="Ground floor", building=self.building)
        group.rooms.add(self.room)
        response = self.client.get(
            reverse("room_schedule/room_group", args=[self.building.pk, group.pk]))
        self.assertContains(response, "Morning Lecture")
        self.assertContains(response, self.placed(540, 600))
        self.assertNotContains(response, "Evening Class")

    # ── Foyer ──

    def test_foyer_lists_only_what_is_still_to_come(self):
        response = self.foyer()
        self.assertNotContains(response, "Morning Lecture")
        self.assertContains(response, "Current Workshop")
        # The foyer has no hours, so an evening booking is still listed.
        self.assertContains(response, "Evening Class")

    def test_foyer_dates_only_bookings_that_are_not_today(self):
        response = self.foyer()
        self.assertNotContains(response, "Today")
        self.assertContains(response, "Sat 14 Nov")
        self.assertContains(response, "bi-calendar4-event", count=1)

    def test_foyer_empty_room_has_no_stray_icons(self):
        Event.objects.filter(room=self.room).delete()
        response = self.foyer()
        self.assertContains(response, "No bookings", count=2)
        self.assertNotContains(response, "bi-clock")
        self.assertNotContains(response, "bi-calendar4-event")

    # ── Both ──

    def test_neither_page_adds_its_own_screensaver(self):
        # EdGEL's display plugin creates the screensaver element itself.
        for name, get in (("grid", self.grid), ("foyer", self.foyer)):
            with self.subTest(page=name):
                self.assertNotContains(get(), "hero-bg")
