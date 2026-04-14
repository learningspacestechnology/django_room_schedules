from django.conf import settings

API_KEY = getattr(settings, 'ARTIFAX_API_KEY', False)
if not API_KEY:
    raise Exception("ARTIFAX_API_KEY not set in settings.py")

BASE_ADDRESS = getattr(settings, 'ARTIFAX_BASE_ADDRESS', False)
if not BASE_ADDRESS:
    raise Exception("ARTIFAX_BASE_ADDRESS not set in settings.py")
HOUR_BREAK_POINT = getattr(settings, 'HOUR_BREAK_POINT', 4)
O365_CLIENT_ID = getattr(settings, 'O365_CLIENT_ID', False)
if not O365_CLIENT_ID:
    raise Exception("O365_CLIENT_ID not set in settings.py")
O365_CLIENT_SECRET = getattr(settings, 'O365_CLIENT_SECRET', False)
if not O365_CLIENT_SECRET:
    raise Exception("O365_CLIENT_SECRET not set in settings.py")
O365_TENANT_ID = getattr(settings, 'O365_TENANT_ID', False)
if not O365_TENANT_ID:
    raise Exception("O365_TENANT_ID not set in settings.py")

# Optional — set both to use delegated (ROPC) auth instead of application auth.
# The service account must have Exchange read access on the room mailboxes.
O365_DELEGATED_USERNAME = getattr(settings, 'O365_DELEGATED_USERNAME', None)
O365_DELEGATED_PASSWORD = getattr(settings, 'O365_DELEGATED_PASSWORD', None)