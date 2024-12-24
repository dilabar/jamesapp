from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from .models import Agency, Subaccount, Role, Configuration
from .forms import SubaccountForm, ConfigurationForm

# Create a new subaccount
@login_required
def create_subaccount(request):
    agency = Agency.objects.get(user=request.user)
    
    if request.method == "POST":
        form = SubaccountForm(request.POST)
        if form.is_valid():
            subaccount = form.save(commit=False)
            subaccount.agency = agency
            subaccount.save()
            # Create default configuration for the subaccount
            Configuration.objects.create(subaccount=subaccount)
            return redirect('agency/agency_dashboard', agency_id=agency.id)
    else:
        form = SubaccountForm()

    return render(request, 'agency/create_subaccount.html', {'form': form, 'agency': agency})

# Configure a subaccount's settings (CRM, Automations)
@login_required
def configure_subaccount(request, subaccount_id):
    subaccount = Subaccount.objects.get(id=subaccount_id)
    configuration = subaccount.configuration
    
    if request.method == "POST":
        form = ConfigurationForm(request.POST, instance=configuration)
        if form.is_valid():
            form.save()
            return redirect('subaccount_dashboard', subaccount_id=subaccount.id)
    else:
        form = ConfigurationForm(instance=configuration)

    return render(request, 'configure_subaccount.html', {'form': form, 'subaccount': subaccount})
