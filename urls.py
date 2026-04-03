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

from .views import show_venue, show_room, room_led_status, book_adhoc, room_state_hash, css_diagnostic

urlpatterns = [
    path('<int:venue_id>', show_venue, name="event_schedule/venue"),
    path('<int:venue_id>/<int:room_id>', show_room, name="event_schedule/room"),
    path('<int:venue_id>/<int:room_id>/LED', room_led_status, name="event_schedule/room_led"),
    path('<int:venue_id>/<int:room_id>/book', book_adhoc, name="event_schedule/book_adhoc"),
    path('<int:venue_id>/<int:room_id>/state_hash', room_state_hash, name="event_schedule/room_state_hash"),
    path('<int:venue_id>/<int:room_id>/diagnostic', css_diagnostic, name="event_schedule/css_diagnostic"),
]
