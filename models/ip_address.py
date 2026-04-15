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

    class Meta:
        verbose_name = "IP address"
        verbose_name_plural = "IP addresses"
        constraints = [
            models.CheckConstraint(
                check=(
                    models.Q(room__isnull=False, building__isnull=True)
                    | models.Q(room__isnull=True, building__isnull=False)
                ),
                name="ip_address_room_xor_building",
            ),
        ]

    def clean(self):
        super().clean()
        if self.room and self.building:
            raise ValidationError("An IP address must belong to either a room or a building, not both.")
        if not self.room and not self.building:
            raise ValidationError("An IP address must belong to a room or a building.")

    def __str__(self):
        return self.ip_address
