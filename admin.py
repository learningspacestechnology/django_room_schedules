from django.contrib import admin
from django.core.exceptions import ValidationError
from django.utils.html import format_html
from unfold.admin import ModelAdmin, TabularInline

from room_schedules.models import Building, Room, IpAddress, RoomGroup


class IpAddressInline(TabularInline):
    model = IpAddress
    extra = 1


class RoomIpAddressInline(IpAddressInline):
    verbose_name = "IP address"
    verbose_name_plural = "IP addresses"
    fk_name = 'room'
    fields = ('ip_address',)


class BuildingIpAddressInline(IpAddressInline):
    verbose_name = "IP address"
    verbose_name_plural = "IP addresses"
    fk_name = 'building'
    fields = ('ip_address',)


class RoomGroupIpAddressInline(IpAddressInline):
    verbose_name = "IP address"
    verbose_name_plural = "IP addresses"
    fk_name = 'room_group'
    fields = ('ip_address',)


class RoomInline(TabularInline):
    model = Room
    extra = 0
    fields = ('name', 'o365_calendar_email', 'allow_booking')


class RoomGroupInline(TabularInline):
    model = RoomGroup
    extra = 0
    fields = ('name', 'default_display')
    show_change_link = True


@admin.register(Building)
class BuildingAdmin(ModelAdmin):
    list_display = ('id', 'name', 'default_display', 'grid_link', 'foyer_link')
    list_display_links = ('id', 'name')
    search_fields = ('name',)
    inlines = [BuildingIpAddressInline, RoomInline, RoomGroupInline]

    def grid_link(self, obj):
        return format_html(
            '<a class="inline-block font-semibold h-6 leading-6 px-2 rounded-default text-[11px] uppercase whitespace-nowrap bg-green-100 text-green-700 dark:bg-green-500/20 dark:text-green-400" href="/event_schedules/{}">Grid</a>',
            obj.id,
        )
    grid_link.short_description = 'Grid'

    def foyer_link(self, obj):
        return format_html(
            '<a class="inline-block font-semibold h-6 leading-6 px-2 rounded-default text-[11px] uppercase whitespace-nowrap bg-blue-100 text-blue-700 dark:bg-blue-500/20 dark:text-blue-400" href="/event_schedules/{}/foyer">Foyer</a>',
            obj.id,
        )
    foyer_link.short_description = 'Foyer'


@admin.register(Room)
class RoomAdmin(ModelAdmin):
    list_display = ('id', 'name', 'building', 'o365_calendar_email', 'allow_booking', 'screen_link')
    list_display_links = ('id', 'name')
    search_fields = ('name', 'building__name')
    list_filter = ('building', 'groups')
    list_select_related = ('building',)
    inlines = [RoomIpAddressInline]

    def screen_link(self, obj):
        return format_html(
            '<a class="inline-block font-semibold h-6 leading-6 px-2 rounded-default text-[11px] uppercase whitespace-nowrap bg-primary-100 text-primary-700 dark:bg-primary-500/20 dark:text-primary-400" href="/event_schedules/{}/{}">Screen</a>',
            obj.building_id, obj.id,
        )
    screen_link.short_description = 'Screen Link'


@admin.register(RoomGroup)
class RoomGroupAdmin(ModelAdmin):
    list_display = ('id', 'name', 'building', 'default_display', 'grid_link', 'foyer_link')
    list_display_links = ('id', 'name')
    search_fields = ('name', 'building__name')
    list_filter = ('building',)
    list_select_related = ('building',)
    filter_horizontal = ('rooms',)
    inlines = [RoomGroupIpAddressInline]

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        if obj is not None and 'rooms' in form.base_fields:
            form.base_fields['rooms'].queryset = Room.objects.filter(building=obj.building)
        return form

    def save_related(self, request, form, formsets, change):
        super().save_related(request, form, formsets, change)
        instance = form.instance
        mismatched = instance.rooms.exclude(building_id=instance.building_id)
        if mismatched.exists():
            names = ", ".join(r.name for r in mismatched)
            raise ValidationError(
                "All rooms in a group must belong to the same building as the group "
                "({}). Mismatched rooms: {}".format(instance.building.name, names)
            )

    def grid_link(self, obj):
        return format_html(
            '<a class="inline-block font-semibold h-6 leading-6 px-2 rounded-default text-[11px] uppercase whitespace-nowrap bg-green-100 text-green-700 dark:bg-green-500/20 dark:text-green-400" href="/event_schedules/{}/group/{}">Grid</a>',
            obj.building_id, obj.id,
        )
    grid_link.short_description = 'Grid'

    def foyer_link(self, obj):
        return format_html(
            '<a class="inline-block font-semibold h-6 leading-6 px-2 rounded-default text-[11px] uppercase whitespace-nowrap bg-blue-100 text-blue-700 dark:bg-blue-500/20 dark:text-blue-400" href="/event_schedules/{}/group/{}/foyer">Foyer</a>',
            obj.building_id, obj.id,
        )
    foyer_link.short_description = 'Foyer'
