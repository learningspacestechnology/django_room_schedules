"""The O365 pages require `room_schedules.change_room`, not just staff status.

They move, assign and bulk-assign display rooms. Wrapped only in `admin_view`,
any staff account could POST to them, whatever its permissions.

The views are called directly rather than through the client, so these tests
do not depend on whatever middleware the host project puts in front of /admin/.
"""

from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.exceptions import PermissionDenied
from django.test import RequestFactory, TestCase

from room_schedules.admin import (o365_assigned_view, o365_sync_now_view,
                                  o365_unassigned_view)

VIEWS = (o365_assigned_view, o365_unassigned_view, o365_sync_now_view)


class O365PermissionTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        cls.staff = User.objects.create_user('staff', is_staff=True)
        cls.editor = User.objects.create_user('editor', is_staff=True)
        cls.editor.user_permissions.add(Permission.objects.get(
            content_type__app_label='room_schedules', codename='change_room'))

    def _request(self, user, method='get'):
        request = getattr(RequestFactory(), method)('/admin/room_schedules/o365/')
        request.user = user
        return request

    def test_staff_without_the_permission_is_refused(self):
        for view in VIEWS:
            for method in ('get', 'post'):
                with self.subTest(view=view.__name__, method=method):
                    with self.assertRaises(PermissionDenied):
                        view(self._request(self.staff, method))

    def test_sync_is_not_dispatched_without_the_permission(self):
        with patch('room_schedules.admin.sync_o365_rooms') as sync:
            with self.assertRaises(PermissionDenied):
                o365_sync_now_view(self._request(self.staff, 'post'))
        sync.delay.assert_not_called()

    def test_room_editor_gets_through(self):
        # GET on the sync view only redirects back, so nothing is dispatched.
        for view in VIEWS:
            with self.subTest(view=view.__name__):
                self.assertIn(view(self._request(self.editor)).status_code, (200, 302))
