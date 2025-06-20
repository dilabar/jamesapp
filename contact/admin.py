from django.contrib import admin
from . models import *
# Register your models here.
@admin.register(Campaign)
class CampaignAdmin(admin.ModelAdmin):
    list_display = (
        'name', 'campaign_type', 'status',
        'scheduled_at', 'scheduled_at_utc',
        'timezone', 'created_at'
    )
    readonly_fields = ('created_at',)

    # Optional: agar aap custom fields specify kar rahe ho
    fields = (
        'user', 'campaign_type', 'name', 'subject', 'content',
        'lists', 'individual_contacts', 'scheduled_at',
        'scheduled_at_utc', 'timezone', 'status', 'created_at'
    )
admin.site.register(Contact)
admin.site.register(List)
admin.site.register(ListContact)
admin.site.register(CustomField)
admin.site.register(BulkAction)
admin.site.register(Email)
admin.site.register(PhoneNumber)
admin.site.register(RevokedTask)
