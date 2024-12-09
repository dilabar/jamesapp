from django.contrib import admin

from .models import CalendarConnection

# Register your models here.
@admin.register(CalendarConnection)
class CalendarConnectionAdmin(admin.ModelAdmin):
    list_display = ('provider', 'is_default')
    search_fields = ('provider', 'is_default')