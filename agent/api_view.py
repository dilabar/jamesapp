import requests
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required

@login_required
def call_history(request):
    
    return render(request, 'new/call_history.html')
@login_required
def call_detail(request):
    
    return render(request, 'new/call_details.html')
@login_required
def agent_setup(request):
    
    return render(request, 'new/list.html')