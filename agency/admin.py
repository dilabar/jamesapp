from django.contrib import admin

# Register your models here.
from .models import *

admin.site.register(AgencyAccount)
admin.site.register(SubAccountProfile)
admin.site.register(AccountSwitchLog)
admin.site.register(User)
admin.site.register(Role)