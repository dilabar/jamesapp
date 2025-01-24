from django.contrib import admin
from . models import *
from django.core.paginator import Paginator

# Register your models here.
admin.site.register(Campaign)
@admin.register(Contact)
class ContactAdmin(admin.ModelAdmin):
    list_per_page = 500
    list_max_show_all = 1000
    paginator = Paginator

@admin.register(List)
class ListAdmin(admin.ModelAdmin):
    list_per_page = 10
    list_max_show_all = 500
    paginator = Paginator
admin.site.register(ListContact)
admin.site.register(Email)
admin.site.register(PhoneNumber)
admin.site.register(BackgroundJob)