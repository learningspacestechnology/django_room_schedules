from django.db import models

from room_schedules.models import Room


class Event(models.Model):
    name = models.CharField(max_length=200)
    room = models.ForeignKey(Room, on_delete=models.CASCADE)
    organiser = models.CharField(max_length=200)
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    artifax_id = models.IntegerField(unique=True, null=True, blank=True)
    o365_event_id = models.CharField(max_length=500, unique=True, null=True, blank=True)
    cancelled = models.BooleanField(default=False)

    def __str__(self):
        return "{}: {}".format(self.pk, self.name)

    class Meta:
        ordering = ['start_time', 'end_time']


