from itertools import groupby

from django.contrib import admin, messages
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404, redirect
from django.template.response import TemplateResponse
from django.urls import path, reverse
from django.utils.html import format_html
from unfold.admin import ModelAdmin, TabularInline
from unfold.decorators import action

from room_schedules.models import Building, O365Room, Room, IpAddress, RoomGroup
from room_schedules.tasks import sync_o365_rooms


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
    list_filter = ('screensaver_enabled',)
    inlines = [BuildingIpAddressInline, RoomInline, RoomGroupInline]
    actions_detail = ['discover_rooms']
    fieldsets = (
        (None, {'fields': ('name',)}),
        ('Display', {'fields': ('default_display', 'pagination_duration_seconds')}),
        ('Screensaver', {
            'fields': (
                'screensaver_enabled',
                'content_duration_seconds',
                'screensaver_duration_seconds',
            ),
        }),
    )

    @action(description="Sync O365 rooms now", url_path="sync-o365-rooms")
    def discover_rooms(self, request, object_id):
        building = get_object_or_404(Building, pk=object_id)
        sync_o365_rooms.delay()
        messages.info(
            request,
            "O365 room sync dispatched. New rooms will appear in the "
            "\u201cO365 Rooms \u2192 Unassigned\u201d view once the worker finishes.",
        )
        return redirect(reverse('admin:room_schedules_building_change', args=[building.pk]))

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
    list_display = ('id', 'name', 'display_name', 'building', 'o365_calendar_email', 'allow_booking', 'screen_link')
    list_display_links = ('id', 'name')
    search_fields = ('name', 'display_name', 'building__name')
    list_filter = ('building', 'groups', 'screensaver_enabled')
    list_select_related = ('building',)
    inlines = [RoomIpAddressInline]
    fieldsets = (
        (None, {
            'fields': ('name', 'display_name', 'building', 'o365_calendar_email', 'allow_booking'),
        }),
        ('Display', {'fields': ('pagination_duration_seconds',)}),
        ('Screensaver', {
            'fields': (
                'screensaver_enabled',
                'content_duration_seconds',
                'screensaver_duration_seconds',
            ),
        }),
    )

    def screen_link(self, obj):
        return format_html(
            '<a class="inline-block font-semibold h-6 leading-6 px-2 rounded-default text-[11px] uppercase whitespace-nowrap bg-primary-100 text-primary-700 dark:bg-primary-500/20 dark:text-primary-400" href="/event_schedules/{}/{}">Screen</a>',
            obj.building_id, obj.id,
        )
    screen_link.short_description = 'Screen Link'


# ----------------------------------------------------------------------
# Custom O365 room management views (registered at admin-site level so
# URLs resolve under /admin/room_schedules/ rather than /admin/room_schedules/room/)
# ----------------------------------------------------------------------


def o365_sync_now_view(request):
    referer = request.META.get('HTTP_REFERER') or reverse('admin:room_schedules_o365_unassigned')
    if request.method != 'POST':
        return redirect(referer)
    sync_o365_rooms.delay()
    messages.info(
        request,
        "O365 sync dispatched \u2014 the room list will refresh within a few minutes.",
    )
    return redirect(referer)


def o365_assigned_view(request):
    if request.method == 'POST':
        action_name = request.POST.get('action')
        if action_name == 'move':
            _handle_move(request)
        elif action_name == 'toggle_booking':
            _handle_toggle_booking(request)
        return redirect(reverse('admin:room_schedules_o365_assigned'))

    rooms = list(
        Room.objects.filter(
            o365_calendar_email__isnull=False,
        ).select_related('building').order_by('building__name', 'name')
    )
    grouped = [
        (building, list(items))
        for building, items in groupby(rooms, key=lambda r: r.building)
    ]

    context = {
        **admin.site.each_context(request),
        'title': 'O365 Rooms \u2014 Assigned per Building',
        'grouped_rooms': grouped,
        'buildings': list(Building.objects.order_by('name')),
        'opts': Room._meta,
        'active_tab': 'assigned',
        'assigned_url': reverse('admin:room_schedules_o365_assigned'),
        'unassigned_url': reverse('admin:room_schedules_o365_unassigned'),
        'sync_now_url': reverse('admin:room_schedules_o365_sync_now'),
    }
    return TemplateResponse(
        request,
        'admin/room_schedules/room/o365_assigned.html',
        context,
    )


def _assigned_room_by_email():
    """Return {email: Room} for every Room that has an o365 email."""
    mapping = {}
    for room in Room.objects.exclude(o365_calendar_email__isnull=True) \
                            .exclude(o365_calendar_email='') \
                            .select_related('building'):
        mapping[room.o365_calendar_email] = room
    return mapping


def o365_unassigned_view(request):
    if request.method == 'POST':
        action_name = request.POST.get('action')
        if action_name == 'assign':
            _handle_assign(request)
        elif action_name == 'bulk_assign':
            _handle_bulk_assign(request)
        return redirect(reverse('admin:room_schedules_o365_unassigned'))

    assigned_by_email = _assigned_room_by_email()
    assigned_emails = set(assigned_by_email)

    unassigned_qs = O365Room.objects.filter(
        missing_from_tenant=False,
        no_calendar_access=False,
    ).exclude(email__in=assigned_emails).order_by('building_hint', 'name')
    grouped_unassigned = [
        (hint or '(no building hint from O365)', list(items))
        for hint, items in groupby(unassigned_qs, key=lambda r: r.building_hint)
    ]

    no_access_qs = list(O365Room.objects.filter(no_calendar_access=True).order_by('name'))
    missing_qs = list(O365Room.objects.filter(missing_from_tenant=True).order_by('name'))
    for room in no_access_qs + missing_qs:
        room.assigned_room = assigned_by_email.get(room.email)

    context = {
        **admin.site.each_context(request),
        'title': 'O365 Rooms \u2014 Unassigned',
        'grouped_unassigned': grouped_unassigned,
        'missing_rooms': missing_qs,
        'no_access_rooms': no_access_qs,
        'buildings': list(Building.objects.order_by('name')),
        'opts': Room._meta,
        'active_tab': 'unassigned',
        'assigned_url': reverse('admin:room_schedules_o365_assigned'),
        'unassigned_url': reverse('admin:room_schedules_o365_unassigned'),
        'sync_now_url': reverse('admin:room_schedules_o365_sync_now'),
    }
    return TemplateResponse(
        request,
        'admin/room_schedules/room/o365_unassigned.html',
        context,
    )


def _resolve_building(request, field='building_id'):
    building_id = request.POST.get(field)
    if not building_id:
        messages.error(request, "Select a building.")
        return None
    try:
        return Building.objects.get(pk=building_id)
    except Building.DoesNotExist:
        messages.error(request, "That building no longer exists.")
        return None


def _handle_toggle_booking(request):
    room_id = request.POST.get('room_id')
    if not room_id:
        return
    try:
        room = Room.objects.get(pk=room_id)
    except Room.DoesNotExist:
        messages.error(request, "Room not found.")
        return
    room.allow_booking = not room.allow_booking
    room.save(update_fields=['allow_booking'])
    state = "enabled" if room.allow_booking else "disabled"
    messages.success(request, f"Adhoc booking {state} for {room.label}.")


def _handle_move(request):
    room_id = request.POST.get('room_id')
    if not room_id:
        return
    try:
        room = Room.objects.get(pk=room_id)
    except Room.DoesNotExist:
        messages.error(request, "Room not found.")
        return
    building = _resolve_building(request)
    if building is None:
        return
    if room.building_id == building.pk:
        messages.info(request, f"{room.name} is already in {building.name}.")
        return
    old_building_name = room.building.name
    room.move_to_building(building)
    messages.success(
        request,
        f"Moved {room.name} from {old_building_name} to {building.name}.",
    )


def _handle_assign(request):
    o365_room_id = request.POST.get('o365_room_id')
    if not o365_room_id:
        return
    try:
        o365_room = O365Room.objects.get(pk=o365_room_id)
    except O365Room.DoesNotExist:
        messages.error(request, "O365 room not found.")
        return
    building = _resolve_building(request)
    if building is None:
        return
    if Room.objects.filter(o365_calendar_email=o365_room.email).exists():
        messages.info(request, f"{o365_room.name} is already assigned.")
        return
    Room.objects.create(
        name=o365_room.name,
        building=building,
        o365_calendar_email=o365_room.email,
    )
    messages.success(request, f"Assigned {o365_room.name} to {building.name}.")


def _handle_bulk_assign(request):
    o365_room_ids = request.POST.getlist('o365_room_ids')
    if not o365_room_ids:
        messages.info(request, "No rooms selected.")
        return
    building = _resolve_building(request)
    if building is None:
        return
    already_assigned = set(
        Room.objects.exclude(o365_calendar_email__isnull=True)
                    .values_list('o365_calendar_email', flat=True)
    )
    created = 0
    for o365_room in O365Room.objects.filter(pk__in=o365_room_ids):
        if o365_room.email in already_assigned:
            continue
        Room.objects.create(
            name=o365_room.name,
            building=building,
            o365_calendar_email=o365_room.email,
        )
        created += 1
    messages.success(
        request,
        f"Assigned {created} room(s) to {building.name}.",
    )


def get_o365_admin_urls():
    return [
        path(
            'room_schedules/o365_assigned/',
            admin.site.admin_view(o365_assigned_view),
            name='room_schedules_o365_assigned',
        ),
        path(
            'room_schedules/o365_unassigned/',
            admin.site.admin_view(o365_unassigned_view),
            name='room_schedules_o365_unassigned',
        ),
        path(
            'room_schedules/o365_sync_now/',
            admin.site.admin_view(o365_sync_now_view),
            name='room_schedules_o365_sync_now',
        ),
    ]


@admin.register(RoomGroup)
class RoomGroupAdmin(ModelAdmin):
    list_display = ('id', 'name', 'building', 'default_display', 'grid_link', 'foyer_link')
    list_display_links = ('id', 'name')
    search_fields = ('name', 'building__name')
    list_filter = ('building', 'screensaver_enabled')
    list_select_related = ('building',)
    filter_horizontal = ('rooms',)
    inlines = [RoomGroupIpAddressInline]
    fieldsets = (
        (None, {'fields': ('name', 'building', 'rooms')}),
        ('Display', {'fields': ('default_display', 'pagination_duration_seconds')}),
        ('Screensaver', {
            'fields': (
                'screensaver_enabled',
                'content_duration_seconds',
                'screensaver_duration_seconds',
            ),
        }),
    )

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
