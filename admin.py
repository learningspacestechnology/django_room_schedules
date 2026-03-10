from django.contrib import admin
from unfold.admin import ModelAdmin, TabularInline

from room_schedules.models import Venue, Room


class RoomInline(TabularInline):
    model = Room
    extra = 0
    fields = ('name', 'artifax_id')


@admin.register(Venue)
class VenueAdmin(ModelAdmin):
    list_display = ('name', 'artifax_id')
    search_fields = ('name',)
    inlines = [RoomInline]


@admin.register(Room)
class RoomAdmin(ModelAdmin):
    list_display = ('name', 'venue', 'artifax_id')
    search_fields = ('name', 'venue__name')
    list_filter = ('venue',)
    list_select_related = ('venue',)
