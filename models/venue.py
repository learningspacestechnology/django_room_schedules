from django.db import models
from django.urls import reverse


class Building(models.Model):
    name = models.CharField(max_length=100)
    ip_address = models.GenericIPAddressField(null=True, blank=True, unique=True, verbose_name="IP address")

    def __str__(self):
        return "{}: {}".format(self.pk, self.name)

    def get_absolute_url(self):
        return reverse('room_schedule/building', args=[str(self.id)])

    def update_events(self):
        from room_schedules.models import Room, Event
        from room_schedules import o365_requests

        for room in self.room_set.filter(o365_calendar_email__isnull=False).exclude(o365_calendar_email=''):
            events = o365_requests.get_todays_events(room.o365_calendar_email)
            o365_ids = []
            new_events = 0
            for e in events:
                ev, created = Event.objects.update_or_create(
                    o365_event_id=e['id'],
                    defaults={
                        'name': e['name'][:200],
                        'organiser': e['organiser'][:200],
                        'room': room,
                        'start_time': e['start_time'],
                        'end_time': e['end_time'],
                        'cancelled': e['cancelled'],
                    },
                )
                o365_ids.append(ev.id)
                if created:
                    new_events += 1
            Event.objects.filter(room=room, o365_event_id__isnull=False).exclude(
                pk__in=o365_ids
            ).delete()
            print("{}/{} (O365) created {} events and updated {}".format(
                self.name, room.name, new_events, len(o365_ids) - new_events
            ))
