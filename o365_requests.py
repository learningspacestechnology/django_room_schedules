import asyncio
import json
import httplib2
import httpx
import msal
from datetime import datetime, timedelta, timezone

from django.conf import settings

from room_schedules.settings import (
    HOUR_BREAK_POINT,
    O365_CLIENT_ID, O365_CLIENT_SECRET, O365_TENANT_ID,
    O365_DELEGATED_USERNAME, O365_DELEGATED_PASSWORD,
)

GRAPH_API = "https://graph.microsoft.com/v1.0"

# Module-level singleton so MSAL's in-memory token cache is reused across rooms
# within a single Celery worker process, avoiding a token request per room.
_msal_app = None


def _get_msal_app():
    global _msal_app
    if _msal_app is None:
        _msal_app = msal.ConfidentialClientApplication(
            client_id=O365_CLIENT_ID,
            client_credential=O365_CLIENT_SECRET,
            authority=f"https://login.microsoftonline.com/{O365_TENANT_ID}",
        )
    return _msal_app


def _get_access_token():
    app = _get_msal_app()
    if O365_DELEGATED_USERNAME and O365_DELEGATED_PASSWORD:
        result = app.acquire_token_by_username_password(
            username=O365_DELEGATED_USERNAME,
            password=O365_DELEGATED_PASSWORD,
            scopes=["https://graph.microsoft.com/Calendars.ReadWrite"],
        )
    else:
        result = app.acquire_token_for_client(
            scopes=["https://graph.microsoft.com/.default"]
        )
    if "access_token" not in result:
        raise RuntimeError(
            f"O365 authentication failed: {result.get('error_description', result)}"
        )
    return result["access_token"]


async def get_todays_events(room_email, limit=100):
    """
    Fetch today's events for an O365 room resource mailbox via the Microsoft Graph API.

    Uses the same fringe-day boundary as the Artifax integration:
    the day runs from HOUR_BREAK_POINT (04:00) to 03:59 the next morning.

    Pass `limit=1` to perform a cheap access-check probe.

    Returns a list of dicts:
        {id, name, organiser, start_time, end_time, cancelled}
    where start_time and end_time are timezone-aware UTC datetimes (Graph API's default).
    """
    now = datetime.now()
    if now.hour < HOUR_BREAK_POINT:
        start = (now - timedelta(days=1)).replace(
            hour=HOUR_BREAK_POINT, minute=0, second=0, microsecond=0
        )
    else:
        start = now.replace(hour=HOUR_BREAK_POINT, minute=0, second=0, microsecond=0)
    end = start + timedelta(hours=24) - timedelta(seconds=1)

    token = await asyncio.to_thread(_get_access_token)
    url = (
        f"{GRAPH_API}/users/{room_email}/calendarView"
        f"?startDateTime={start.isoformat()}&endDateTime={end.isoformat()}"
        f"&$select=id,subject,organizer,start,end,isCancelled"
        f"&$top={limit}"
    )
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.get(
            url,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
        )

    if resp.status_code != 200:
        raise RuntimeError(
            f"Graph API error {resp.status_code} for {room_email}: {resp.text}"
        )

    results = []
    for item in resp.json().get("value", []):
        results.append({
            "id": item["id"],
            "name": item.get("subject", ""),
            "organiser": item.get("organizer", {}).get("emailAddress", {}).get("name", ""),
            "start_time": datetime.fromisoformat(item["start"]["dateTime"].rstrip("Z")).replace(tzinfo=timezone.utc),
            "end_time": datetime.fromisoformat(item["end"]["dateTime"].rstrip("Z")).replace(tzinfo=timezone.utc),
            "cancelled": item.get("isCancelled", False),
        })
    return results


async def filter_accessible_rooms(rooms, *, concurrency=20):
    """Split `rooms` into (accessible, inaccessible) by probing each calendar.

    A room is accessible iff get_todays_events(email, limit=1) returns without
    raising RuntimeError. A Semaphore bounds concurrent Graph requests so large
    tenants don't fan out unboundedly.
    """
    sem = asyncio.Semaphore(concurrency)

    async def probe(room):
        async with sem:
            try:
                await get_todays_events(room['email'], limit=1)
                return True
            except RuntimeError:
                return False

    flags = await asyncio.gather(*(probe(r) for r in rooms))
    accessible = [r for r, ok in zip(rooms, flags) if ok]
    inaccessible = [r for r, ok in zip(rooms, flags) if not ok]
    return accessible, inaccessible


def _graph_get_paginated_manual(url, token, page_size):
    """Yield items from a paginated Graph endpoint, following @odata.nextLink."""
    h = httplib2.Http(timeout=60)
    count=0
    while True:
        response, content = h.request(
            url+f"&$top={page_size}&$skip={count}",
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
        )
        if response.status != 200:
            raise RuntimeError(
                f"Graph API error {response.status} for {url}: {content}"
            )
        payload = json.loads(content)
        value = payload.get("value", [])
        count += len(value)
        for item in value:
            yield item
        if len(value) < page_size:
            break


def _room_item_to_dict(item):
    email = item.get("emailAddress")
    if not email:
        return None
    return {
        "email": email,
        "name": item.get("displayName", ""),
        "building": item.get("building", ""),
        "floor": item.get("floorNumber"),
        "capacity": item.get("capacity"),
    }


def list_tenant_rooms():
    """Return all room mailboxes in the tenant via Graph /places.

    Queries /places/microsoft.graph.room, paginating 100 results at a time
    via manual $skip/$top so tenants with >100 rooms aren't truncated, and
    deduplicates by email.

    Requires Place.Read.All on the app registration.

    Returns a list of dicts: {email, name, building, floor, capacity}.
    """
    token = _get_access_token()
    select = "$select=displayName,emailAddress,building,floorNumber,capacity"

    rooms_by_email = {} 

    for item in _graph_get_paginated_manual(
        f"{GRAPH_API}/places/microsoft.graph.room?{select}", token, 100
    ):
        room = _room_item_to_dict(item)
        if room:
            rooms_by_email.setdefault(room["email"], room)

    print(len(rooms_by_email), "rooms found in tenant via Graph API")
    return list(rooms_by_email.values())


def create_adhoc_booking(room_email, start_dt, end_dt):
    """Create an 'Adhoc Booking' event on the room's O365 calendar.

    start_dt and end_dt are naive local datetimes (Europe/London).
    Returns the new event's O365 id string.
    """
    token = _get_access_token()
    h = httplib2.Http()
    url = f"{GRAPH_API}/users/{room_email}/calendar/events"
    body = json.dumps({
        "subject": "Adhoc Booking",
        "start": {"dateTime": start_dt.isoformat(), "timeZone": settings.TIME_ZONE},
        "end":   {"dateTime": end_dt.isoformat(),   "timeZone": settings.TIME_ZONE},
    })
    response, content = h.request(
        url,
        method="POST",
        body=body,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
    )
    if response.status not in (200, 201):
        raise RuntimeError(
            f"Graph API error {response.status} creating adhoc booking for {room_email}: {content}"
        )
    return json.loads(content)["id"]
