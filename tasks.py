import asyncio
import datetime

import httpx
from celery import shared_task

from room_schedules.models import Building, Event, O365Room, Room
from room_schedules.o365_requests import filter_accessible_rooms, list_tenant_rooms


@shared_task(name='room_schedules.tasks.build_schedule')
def build_schedule():
    for building in Building.objects.all():
        building.update_events()


@shared_task(name='room_schedules.tasks.cleanup_schedule')
def cleanup_schedule():
    Event.objects.filter(start_time__lt=datetime.datetime.now() - datetime.timedelta(days=2)).delete()


@shared_task(
    name='room_schedules.tasks.sync_o365_rooms',
    autoretry_for=(RuntimeError, httpx.TimeoutException, httpx.TransportError, OSError),
    retry_backoff=True,
    retry_backoff_max=600,
    retry_jitter=True,
    max_retries=5,
    soft_time_limit=300,
    time_limit=330,
)
def sync_o365_rooms():
    """Upsert every tenant mailbox into O365Room and keep assigned Rooms' names
    in lock-step with the tenant displayName.

    Every room the tenant returns is reflected in O365Room regardless of whether
    our credentials can read its calendar; the no_calendar_access flag records
    the probe result so the admin UI can surface inaccessible rooms separately.
    An O365Room no longer in the tenant is kept and flagged
    missing_from_tenant=True only when it still backs a real imported Room (so
    the admin can review it in the "Missing from tenant" list); otherwise it is
    deleted as stale inventory. Rooms are never created or deleted here; only
    their name is refreshed to match the corresponding O365Room.
    """
    tenant_rooms = list_tenant_rooms()

    accessible, inaccessible = asyncio.run(filter_accessible_rooms(tenant_rooms))

    def upsert(rooms, *, no_access):
        for r in rooms:
            email = r.get('email')
            if not email:
                continue
            name = (r.get('name') or email)[:200]
            O365Room.objects.update_or_create(
                email=email,
                defaults={
                    'name': name,
                    'building_hint': r.get('building') or '',
                    'no_calendar_access': no_access,
                    'missing_from_tenant': False,
                },
            )
            Room.objects.filter(o365_calendar_email=email).exclude(name=name).update(name=name)

    upsert(accessible, no_access=False)
    upsert(inaccessible, no_access=True)

    seen_emails = {r['email'] for r in tenant_rooms if r.get('email')}
    missing = O365Room.objects.exclude(email__in=seen_emails)

    # Emails that currently back a real, imported Room.
    imported_emails = set(
        Room.objects.exclude(o365_calendar_email__isnull=True)
                    .exclude(o365_calendar_email='')
                    .values_list('o365_calendar_email', flat=True)
    )

    # A mailbox that vanished from the tenant but was never imported as a Room
    # (or whose Room has since been deleted) is just stale inventory — drop it.
    # Ones that still back a real Room are flagged so the admin can review and
    # remove them from the "Missing from tenant" list.
    missing.exclude(email__in=imported_emails).delete()
    missing.filter(email__in=imported_emails).update(missing_from_tenant=True)

    return {'accessible': len(accessible), 'inaccessible': len(inaccessible)}
