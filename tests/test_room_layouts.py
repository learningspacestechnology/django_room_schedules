import datetime

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from room_schedules.models import Building, Event, IpAddress, Room

DEVICE_IP = "10.0.60.1"

LAYOUT_TEMPLATES = {
    Room.DISPLAY_STANDARD: "room_schedules/room_screen_uoe.html",
    Room.DISPLAY_SCREEN: "room_schedules/room_screen.html",
    Room.DISPLAY_TABLET: "room_schedules/room_tablet.html",
}


class RoomLayoutTests(TestCase):
    """The three room layouts, and how a registered device is routed to one."""

    @classmethod
    def setUpTestData(cls):
        cls.building = Building.objects.create(name="Riverside Library")
        cls.room = Room.objects.create(
            name="Seminar Room 1.02",
            building=cls.building,
            o365_calendar_email="seminar-1.02@demo.invalid",
            allow_booking=True,
        )
        IpAddress.objects.create(ip_address=DEVICE_IP, room=cls.room)

    def setUp(self):
        self.client = Client(REMOTE_ADDR=DEVICE_IP)

    def _get(self, layout):
        return self.client.get(self.room.display_url(layout))

    def test_each_layout_renders_its_template(self):
        for layout, template in LAYOUT_TEMPLATES.items():
            with self.subTest(layout=layout):
                response = self._get(layout)
                self.assertEqual(response.status_code, 200)
                self.assertTemplateUsed(response, template)
                self.assertContains(response, "Seminar Room 1.02")

    def test_banner_layouts_show_the_building_name(self):
        # These templates predate the Venue → Building rename.
        for layout in (Room.DISPLAY_SCREEN, Room.DISPLAY_TABLET):
            with self.subTest(layout=layout):
                self.assertContains(
                    self._get(layout), '<div class="venue-name">Riverside Library</div>', html=True)

    def test_every_layout_offers_booking_when_the_room_allows_it(self):
        for layout in LAYOUT_TEMPLATES:
            with self.subTest(layout=layout):
                self.assertContains(self._get(layout), "openBookingModal()")

    def test_no_layout_offers_booking_when_the_room_does_not(self):
        Room.objects.filter(pk=self.room.pk).update(allow_booking=False)
        for layout in LAYOUT_TEMPLATES:
            with self.subTest(layout=layout):
                self.assertNotContains(self._get(layout), "openBookingModal()")

    def test_no_layout_reveals_a_private_booking_subject(self):
        now = timezone.now()
        Event.objects.create(
            name="Confidential Restructure Briefing",
            organiser="Alice Smith",
            room=self.room,
            start_time=now - datetime.timedelta(minutes=10),
            end_time=now + datetime.timedelta(minutes=50),
            sensitivity="private",
        )
        Event.objects.create(
            name="Open Seminar",
            organiser="Bob Jones",
            room=self.room,
            start_time=now + datetime.timedelta(hours=2),
            end_time=now + datetime.timedelta(hours=3),
        )
        for layout in LAYOUT_TEMPLATES:
            with self.subTest(layout=layout):
                response = self._get(layout)
                self.assertNotContains(response, "Confidential Restructure Briefing")
                self.assertContains(response, "Alice Smith")
                self.assertContains(response, "Open Seminar")

    def test_device_is_sent_to_the_rooms_chosen_layout(self):
        auto_route = reverse("room_schedule/auto_route")
        for layout in LAYOUT_TEMPLATES:
            with self.subTest(layout=layout):
                Room.objects.filter(pk=self.room.pk).update(default_display=layout)
                response = self.client.get(auto_route)
                self.assertRedirects(
                    response, self.room.display_url(layout), fetch_redirect_response=False)

    def test_new_rooms_keep_the_standard_layout(self):
        room = Room.objects.create(name="New Room", building=self.building)
        self.assertEqual(room.default_display, Room.DISPLAY_STANDARD)
        self.assertEqual(
            room.get_absolute_url(), reverse("room_schedule/room", args=[self.building.pk, room.pk]))

    def test_unknown_layout_falls_back_to_standard(self):
        self.room.default_display = "retired-layout"
        self.assertEqual(self.room.get_absolute_url(), self.room.display_url(Room.DISPLAY_STANDARD))


class RoomAdminLayoutTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = get_user_model().objects.create_superuser("admin", "admin@demo.invalid", "pw")
        building = Building.objects.create(name="Riverside Library")
        cls.room = Room.objects.create(
            name="Seminar Room 1.02", building=building, default_display=Room.DISPLAY_TABLET)

    def setUp(self):
        self.client.force_login(self.admin)

    def test_room_list_links_every_layout(self):
        response = self.client.get(reverse("admin:room_schedules_room_changelist"))
        self.assertEqual(response.status_code, 200)
        for layout in LAYOUT_TEMPLATES:
            with self.subTest(layout=layout):
                self.assertContains(response, 'href="{}"'.format(self.room.display_url(layout)))

    def test_room_form_offers_the_layout(self):
        url = reverse("admin:room_schedules_room_change", args=[self.room.pk])
        response = self.client.get(url)
        self.assertContains(response, 'name="default_display"')
