from django.db import models


class O365Room(models.Model):
    """Tenant-side inventory of O365 room mailboxes.

    Rewritten by `sync_o365_rooms` on every run. A separate `Room` is created
    when an operator assigns an O365Room to a building; from then on the two
    rows are linked by email only (no FK).
    """

    email = models.EmailField(unique=True)
    name = models.CharField(max_length=200)
    building_hint = models.CharField(
        max_length=200, blank=True, default='',
        help_text="Building name suggested by O365, used to help assign this mailbox to a building. Informational.")
    no_calendar_access = models.BooleanField(
        default=False,
        help_text="Set automatically when the daily sync cannot read this mailbox's calendar.")
    missing_from_tenant = models.BooleanField(
        default=False,
        help_text="Set automatically when this mailbox is no longer found in O365 (e.g. deleted).")

    class Meta:
        ordering = ['building_hint', 'name']

    def __str__(self):
        return "{}: {}".format(self.pk, self.name)
