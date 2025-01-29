from django.contrib import admin

from .models import Bill, CallRate

# Register your models here.
@admin.register(CallRate)
class CallRateAdmin(admin.ModelAdmin):
    list_display = ('name', 'price_per_second', 'is_active')
    list_editable = ('is_active',)
admin.site.register(Bill)