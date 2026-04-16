from django.core.exceptions import ValidationError
from django.db import models


class IpAddress(models.Model):
    ip_address = models.GenericIPAddressField(unique=True, verbose_name="IP address")
    room = models.ForeignKey(
        'Room', null=True, blank=True, on_delete=models.CASCADE, related_name='ip_addresses'
    )
    building = models.ForeignKey(
        'Building', null=True, blank=True, on_delete=models.CASCADE, related_name='ip_addresses'
    )
    room_group = models.ForeignKey(
        'RoomGroup', null=True, blank=True, on_delete=models.CASCADE, related_name='ip_addresses'
    )

    class Meta:
        verbose_name = "IP address"
        verbose_name_plural = "IP addresses"
        constraints = [
            models.CheckConstraint(
                check=(
                    models.Q(room__isnull=False, building__isnull=True, room_group__isnull=True)
                    | models.Q(room__isnull=True, building__isnull=False, room_group__isnull=True)
                    | models.Q(room__isnull=True, building__isnull=True, room_group__isnull=False)
                ),
                name="ip_address_exactly_one_target",
            ),
        ]

    def clean(self):
        super().clean()
        targets = [bool(self.room), bool(self.building), bool(self.room_group)]
        if sum(targets) > 1:
            raise ValidationError(
                "An IP address must belong to exactly one of: a room, a building, or a room group."
            )
        if sum(targets) == 0:
            raise ValidationError(
                "An IP address must belong to a room, a building, or a room group."
            )

    def __str__(self):
        return self.ip_address
