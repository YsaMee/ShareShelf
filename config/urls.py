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
    
    # Auth
    path('', views.login_view, name='login'),
    path('signup/', views.signup_view, name='signup'),
    path('logout/', views.logout_view, name='logout'),
    
    # Main Views
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('browse/', views.browse_view, name='browse'),
    path('item/<int:item_id>/', views.item_detail_view, name='item_detail'),
    
    # Item & Handoff Actions
    path('post-item/', views.post_item_view, name='post_item'),
    path('post-request/', views.post_request_view, name='post_request'),
    path('request-item/<int:item_id>/', views.request_item_view, name='request_item'),
    path('item/<int:item_id>/change-qty/', views.change_qty_view, name='change_qty'),
    path('item/<int:item_id>/toggle-pause/', views.toggle_pause_view, name='toggle_pause'),
    path('item/<int:item_id>/remove/', views.remove_item_view, name='remove_item'),
    
    # Request Lifecycle Actions
    path('request/<int:request_id>/accept/', views.accept_incoming_view, name='accept_incoming'),
    path('request/<int:request_id>/decline/', views.decline_incoming_view, name='decline_incoming'),
    path('request/<int:request_id>/complete/', views.complete_incoming_view, name='complete_incoming'),
    path('request/<int:request_id>/returned/', views.mark_returned_view, name='mark_returned'),
    path('request/<int:request_id>/cancel/', views.cancel_request_view, name='cancel_request'),
    path('request/<int:request_id>/confirm/', views.confirm_handoff_view, name='confirm_handoff'),
    path('request/<int:request_id>/match/<int:item_id>/', views.ask_for_match_view, name='ask_for_match'),
]
