from django.shortcuts import render
from google_auth_oauthlib.flow import Flow
from django.http import HttpResponseBadRequest, JsonResponse, HttpResponseRedirect
from requests import request
from django.utils.timezone import now
from django.db.models import Q
from .models import CalendarConnection

from agent.models import GoogleCalendarEvent

# Create your views here.
def google_oauth(request):
    CLIENT_SECRETS_FILE = "client_secrets.json"
    flow = Flow.from_client_secrets_file(
        CLIENT_SECRETS_FILE,
        scopes=['https://www.googleapis.com/auth/calendar'],
        redirect_uri=f'http://localhost:8000/scheduling/oauth/callback'
    )
    auth_url, state= flow.authorization_url(prompt='consent')
    request.session['oauth_state'] = state
    print(f"Session after setting state: {request.session.get('oauth_state')}")
    print(f"Session after setting auth_url: {auth_url}")
    request.session.modified = True
    return HttpResponseRedirect(auth_url)

def google_oauth_callback(request):
     # Check if state is valid
    state = request.GET.get('state')
    print(f"OAuth State: {request.session.get('oauth_state')},{state}")
    # if not state or state != request.session.get('oauth_state'):
    #     return HttpResponseBadRequest("Invalid state parameter")
    
    CLIENT_SECRETS_FILE = "client_secrets.json"
    # state = request.session['oauth_state']
    flow = Flow.from_client_secrets_file(
        CLIENT_SECRETS_FILE,
        scopes=['https://www.googleapis.com/auth/calendar'],
        state=state,
        redirect_uri=f'http://localhost:8000/scheduling/oauth/callback'
    )
    flow.fetch_token(authorization_response=request.build_absolute_uri())

    credentials = flow.credentials
    CalendarConnection.objects.create(
        user=request.user,
        provider='google',
        credentials={
            'token': credentials.token,
            'refresh_token': credentials.refresh_token,
            'token_uri': credentials.token_uri,
            'client_id': credentials.client_id,
            'client_secret': credentials.client_secret,
            'scopes': credentials.scopes,
        },
        is_default=CalendarConnection.objects.filter(user=request.user).count() == 0  # Set as default if it's the first calendar
    )
    return JsonResponse({"message": "Google Calendar connected successfully"})

def integrations_view(request):
    
    cal =CalendarConnection.objects.filter(user=request.user)
    integrations = [
        {
            "name": "Google Calendar",
            "description": "Connect your Google Calendar to manage events and bookings seamlessly.",
            "icon":f"{request.scheme}://{request.get_host()}/static/img/svg-icon/google-calendar.svg",  # Google Calendar icon URL
            "connect_url": f"{request.scheme}://{request.get_host()}/scheduling/oauth/",
                            
            "is_connected": cal.count() > 0
        }
        
    ]
    return render(request, 'scheduling/integrations_list.html', {'integrations': integrations})








def event_list(request):
    """
    View to list all calendar events.
    """
    events = GoogleCalendarEvent.objects.all().order_by('-start_time')
    current_time = now()
    return render(request, 'scheduling/events_list.html', {'events': events, 'now': current_time})

def event_list_data(request):
    draw = int(request.GET.get('draw', 1))
    start = int(request.GET.get('start', 0))
    length = int(request.GET.get('length', 10))
    search_value = request.GET.get('search[value]', '')

    queryset = GoogleCalendarEvent.objects.all()

    if search_value:
        queryset = queryset.filter(
            Q(summary__icontains=search_value) |
            Q(attendees__icontains=search_value) |
            Q(status__icontains=search_value)
        )

    total = queryset.count()
    events = queryset.order_by('-created_at')[start:start + length]

    data = []
    for event in events:
        event_status_badge = ""
        if event.status == 'cancelled':
            event_status_badge = '<span class="badge bg-danger">Cancelled</span>'
        elif event.status == 'failed':
            event_status_badge = '<span class="badge bg-danger">Failed</span>'
        elif event.status == 'completed' and event.end_time < now():
            event_status_badge = '<span class="badge bg-success">Completed</span>'
        elif event.status == 'pending':
            event_status_badge = '<span class="badge bg-warning">Pending</span>'
        else:
            event_status_badge = '<span class="badge bg-info">Upcoming</span>'

        data.append({
            'summary': event.summary,
            'start_time': event.start_time.strftime('%Y-%m-%d %H:%M'),
            'end_time': event.end_time.strftime('%Y-%m-%d %H:%M'),
            'description': event.description if event.description else 'No description',
            'attendees': ', '.join(event.attendees) if isinstance(event.attendees, list) else event.attendees,
            'calendar_event_id': event.calendar_event_id,
            'calendar_link': event.calendar_link,
            'status': event_status_badge,
            'actions': f'''
                <a href="{event.calendar_link}" target="_blank" class="btn btn-info btn-sm">View Event</a>
            '''
        })

    return JsonResponse({
        'draw': draw,
        'recordsTotal': total,
        'recordsFiltered': total,
        'data': data
    })