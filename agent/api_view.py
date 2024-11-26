from django.http import HttpResponse
import requests
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
import urllib
from django.core.paginator import Paginator
from django.db.models import F
from .models import PhoneCall, ServiceDetail

@login_required
def call_history(request):
    # Fetch phone calls for the logged-in user
    phone_calls = (
        PhoneCall.objects.filter(user=request.user)
        .order_by(F('timestamp').desc(nulls_last=True))  # Order by 'date' descending
    )

    # Apply offset and limit for pagination
    page_number = request.GET.get('page', 1)  # Default to the first page
    limit = 10  # Number of records per page
    offset = (int(page_number) - 1) * limit  # Calculate offset
    paginated_calls = phone_calls[offset:offset + limit]
    # Calculate the total number of pages
    total_records = phone_calls.count()
    total_pages = (total_records + limit - 1) // limit  # Ceil division

    context = {
        'page_obj': paginated_calls,  # Paginated phone calls
        'page_number': page_number,  # Current page number
        'total_pages': total_pages,  # Total number of pages
        'page_range': range(1, total_pages + 1),  # Create a range of pages
    }
    return render(request, 'new/call_history.html', context)
@login_required
def call_detail(request,id):
    obj=PhoneCall.objects.filter(user=request.user,id=id).first()
    context={
        'call_obj':obj
    }
    return render(request, 'new/call_details.html',context)
@login_required
def agent_setup(request):
    
    return render(request, 'new/list.html')

@login_required
def fetch_twilio_recording(request,recording_url):
    recording_url = urllib.parse.unquote(recording_url)
    twilio = ServiceDetail.objects.filter(user=request.user, service_name='twilio').first()
    # Fetch the recording from Twilio
    response = requests.get(recording_url, auth=(twilio.decrypted_account_sid,twilio.decrypted_api_key))
    
    if response.status_code == 200:

        # Serve the recording as an audio file
        return HttpResponse(response.content, content_type="audio/mpeg")
    else:
        return HttpResponse("Recording not found or unauthorized.", status=404)