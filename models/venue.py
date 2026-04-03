from django.db import models
from django.urls import reverse

from room_schedules.artifax_requests import get_todays_events_simple


class Building(models.Model):
    name = models.CharField(max_length=100)
    artifax_id = models.IntegerField(unique=True, null=True, blank=True)

    def __str__(self):
        return "{}: {}".format(self.pk, self.name)

    def get_absolute_url(self):
        return reverse('event_schedule/building', args=[str(self.id)])

    def update_events(self):
        from room_schedules.models import Room, Event
        from room_schedules import o365_requests

        # --- Artifax source ---
        if self.artifax_id:
            events = get_todays_events_simple(self.artifax_id)
            artifax_ids = []
            new_events = 0
            for e in events:
                room, _ = Room.objects.update_or_create(
                    artifax_id=e['room_id'],
                    defaults={'name': e['room_name'], 'building': self},
                )
                ev, created = Event.objects.update_or_create(
                    artifax_id=e['event_id'],
                    defaults={
                        'name': e['activity_detail'][:200],
                        'organiser': e['organiser'][:200],
                        'room': room,
                        'start_time': e['time'],
                        'end_time': e['finish_time'],
                        'cancelled': e['cancelled'],
                    },
                )
                artifax_ids.append(ev.id)
                if created:
                    new_events += 1
            Event.objects.filter(room__building=self, artifax_id__isnull=False).exclude(
                pk__in=artifax_ids
            ).delete()
            print("{} (Artifax) created {} events and updated {}".format(
                self.name, new_events, len(artifax_ids) - new_events
            ))

        # --- O365 source (per room) ---
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
