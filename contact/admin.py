from django.contrib import admin
from . models import *
# Register your models here.
admin.site.register(Campaign)
admin.site.register(Contact)
admin.site.register(List)
admin.site.register(ListContact)
admin.site.register(Email)
admin.site.register(PhoneNumber)