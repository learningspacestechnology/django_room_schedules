"""advertising URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/2.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.urls import path

from .views import show_building_grid, show_building_foyer, building_state_hash, show_room, room_led_status, book_adhoc, room_state_hash, css_diagnostic, auto_route

urlpatterns = [
    path('auto', auto_route, name="room_schedule/auto_route"),
    path('<int:venue_id>', show_building_grid, name="room_schedule/building"),
    path('<int:venue_id>/foyer', show_building_foyer, name="room_schedule/building_foyer"),
    path('<int:venue_id>/state_hash', building_state_hash, name="room_schedule/building_state_hash"),
    path('<int:venue_id>/<int:room_id>', show_room, name="room_schedule/room"),
    path('<int:venue_id>/<int:room_id>/LED', room_led_status, name="room_schedule/room_led"),
    path('<int:venue_id>/<int:room_id>/book', book_adhoc, name="room_schedule/book_adhoc"),
    path('<int:venue_id>/<int:room_id>/state_hash', room_state_hash, name="room_schedule/room_state_hash"),
    path('<int:venue_id>/<int:room_id>/diagnostic', css_diagnostic, name="room_schedule/css_diagnostic"),
]
