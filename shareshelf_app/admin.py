from django.contrib import admin
from .models import Item, Request, UserProfile

admin.site.register((UserProfile, Item, Request))
