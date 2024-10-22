from django.contrib import admin

from agent.models import Agent, PhoneCall

# Register your models here.
@admin.register(Agent)
class AgentAdmin(admin.ModelAdmin):
    list_display = ('agent_id', 'name', 'created_at', 'updated_at')
    search_fields = ('name', 'agent_id')
@admin.register(PhoneCall)
class PhoneCallAdmin(admin.ModelAdmin):
    list_display = ('phone_number', 'call_status', 'timestamp')
    search_fields = ('phone_number', 'call_status')