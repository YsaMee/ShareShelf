"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.1/topics/http/urls/
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
from django.contrib import admin
from django.urls import path
from shareshelf_app import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.login_view, name='login'),
    path('signup/', views.signup_view, name='signup'),
    path('logout/', views.logout_view, name='logout'),
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('browse/', views.browse_view, name='browse'),
    path('items/<int:item_id>/', views.item_detail_view, name='item_detail'),
    path('items/post/', views.post_item_view, name='post_item'),
    path('items/<int:item_id>/request/', views.request_item_view, name='request_item'),
    path('items/<int:item_id>/quantity/', views.change_qty_view, name='change_qty'),
    path('items/<int:item_id>/pause/', views.toggle_pause_view, name='toggle_pause'),
    path('items/<int:item_id>/remove/', views.remove_item_view, name='remove_item'),
    path('requests/post/', views.post_request_view, name='post_request'),
    path('requests/<int:request_id>/accept/', views.accept_incoming_view, name='accept_incoming'),
    path('requests/<int:request_id>/decline/', views.decline_incoming_view, name='decline_incoming'),
    path('requests/<int:request_id>/complete/', views.complete_incoming_view, name='complete_incoming'),
    path('requests/<int:request_id>/returned/', views.mark_returned_view, name='mark_returned'),
    path('requests/<int:request_id>/cancel/', views.cancel_request_view, name='cancel_request'),
    path('requests/<int:request_id>/handoff/', views.confirm_handoff_view, name='confirm_handoff'),
    path('requests/<int:request_id>/matches/<int:item_id>/', views.ask_for_match_view, name='ask_for_match'),
]
