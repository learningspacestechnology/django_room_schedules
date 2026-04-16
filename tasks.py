import datetime
from celery import shared_task
from room_schedules.models import Building, Event, Room
from room_schedules.o365_requests import list_tenant_rooms

@shared_task(name='room_schedules.tasks.build_schedule')
def build_schedule():
    for building in Building.objects.all():
        building.update_events()

@shared_task(name='room_schedules.tasks.cleanup_schedule')
def cleanup_schedule():
    Event.objects.filter(start_time__lt=datetime.datetime.now() - datetime.timedelta(days=2)).delete()

@shared_task(name='room_schedules.tasks.sync_room_names')
def sync_room_names():
    """Refresh Room.name from O365 displayName for every imported room.

    Rooms whose mailbox no longer appears in the tenant are left untouched
    so an operator can review before deletion.
    """
    by_email = {r['email']: r['name'] for r in list_tenant_rooms() if r.get('name')}
    if not by_email:
        return 0

    updated = []
    for room in Room.objects.exclude(o365_calendar_email__isnull=True):
        new_name = by_email.get(room.o365_calendar_email)
        if new_name and new_name != room.name:
            room.name = new_name
            updated.append(room)

    if updated:
        Room.objects.bulk_update(updated, ['name'])
    return len(updated)
