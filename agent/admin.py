from django.contrib import admin

from agent.models import Agent, GoogleCalendarEvent, PhoneCall, ServiceDetail,Conversation

# Register your models here.
@admin.register(Agent)
class AgentAdmin(admin.ModelAdmin):
    list_display = ('agent_id', 'display_name', 'created_at', 'updated_at')
    search_fields = ('display_name', 'agent_id')
@admin.register(PhoneCall)
class PhoneCallAdmin(admin.ModelAdmin):
    list_display = ('phone_number', 'call_status', 'timestamp')
    search_fields = ('phone_number', 'call_status')
@admin.register(ServiceDetail)
class ServiceDetailAdmin(admin.ModelAdmin):
    list_display = ('service_name', 'created_at')
    search_fields = ('service_name', 'created_at')

@admin.register(GoogleCalendarEvent)
class GoogleCalendarEventAdmin(admin.ModelAdmin):
    list_display = ('summary', 'start_time','end_time','status')
    search_fields = ('summary', 'attendees')

admin.site.register(Conversation)

    