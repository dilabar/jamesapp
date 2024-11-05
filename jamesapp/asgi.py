
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'jamesapp.settings')

import django
django.setup()
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from jamesapp.routing import websocket_urlpatterns  # Replace with your app's routing


application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    "websocket": AuthMiddlewareStack(
        URLRouter(
            websocket_urlpatterns
        )
    ),
})
