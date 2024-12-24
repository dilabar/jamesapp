from django.contrib import admin

# Register your models here.
from .models import Agency, Subaccount, Role, Configuration

admin.site.register(Agency)
admin.site.register(Subaccount)
admin.site.register(Role)
admin.site.register(Configuration)