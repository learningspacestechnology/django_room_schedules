import json
import httplib2
import msal
from datetime import datetime, timedelta

from room_schedules.settings import HOUR_BREAK_POINT, O365_CLIENT_ID, O365_CLIENT_SECRET, O365_TENANT_ID

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
    result = _get_msal_app().acquire_token_for_client(
        scopes=["https://graph.microsoft.com/.default"]
    )
    if "access_token" not in result:
        raise RuntimeError(
            f"O365 authentication failed: {result.get('error_description', result)}"
        )
    return result["access_token"]


def get_todays_events(room_email):
    """
    Fetch today's events for an O365 room resource mailbox via the Microsoft Graph API.

    Uses the same fringe-day boundary as the Artifax integration:
    the day runs from HOUR_BREAK_POINT (04:00) to 03:59 the next morning.

    Returns a list of dicts:
        {id, name, organiser, start_time, end_time, cancelled}
    where start_time and end_time are naive datetime objects in local time.
    """
    now = datetime.now()
    if now.hour < HOUR_BREAK_POINT:
        start = (now - timedelta(days=1)).replace(
            hour=HOUR_BREAK_POINT, minute=0, second=0, microsecond=0
        )
    else:
        start = now.replace(hour=HOUR_BREAK_POINT, minute=0, second=0, microsecond=0)
    end = start + timedelta(hours=24) - timedelta(seconds=1)

    token = _get_access_token()
    h = httplib2.Http()
    url = (
        f"{GRAPH_API}/users/{room_email}/calendarView"
        f"?startDateTime={start.isoformat()}&endDateTime={end.isoformat()}"
        f"&$select=id,subject,organizer,start,end,isCancelled"
        f"&$top=100"
    )
    response, content = h.request(
        url,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
    )

    if response.status != 200:
        raise RuntimeError(
            f"Graph API error {response.status} for {room_email}: {content}"
        )

    results = []
    for item in json.loads(content).get("value", []):
        results.append({
            "id": item["id"],
            "name": item.get("subject", ""),
            "organiser": item.get("organizer", {}).get("emailAddress", {}).get("name", ""),
            "start_time": datetime.fromisoformat(item["start"]["dateTime"].rstrip("Z")),
            "end_time": datetime.fromisoformat(item["end"]["dateTime"].rstrip("Z")),
            "cancelled": item.get("isCancelled", False),
        })
    return results
