from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from .models import Agency, Subaccount, Role, Configuration
from .forms import SubaccountForm, ConfigurationForm
from django.core.paginator import Paginator

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
            return redirect('configure_subaccount', subaccount_id=subaccount.id)
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
        subaccount_form = SubaccountForm(request.POST, instance=subaccount)
        if form.is_valid() and subaccount_form.is_valid():
            form.save()
            subaccount_form.save()
            return redirect('subaccount_dashboard', subaccount_id=subaccount.id)
    else:
        form = ConfigurationForm(instance=configuration)
        subaccount_form = SubaccountForm(instance=subaccount)

    return render(request, 'agency/configure_subaccount.html', {'form': form,'subaccount_form':subaccount_form, 'subaccount': subaccount})

def list_subaccounts(request):
    try:
        agency = Agency.objects.get(user=request.user)
    except Agency.DoesNotExist:
        agency = None

    subaccounts = Subaccount.objects.filter(agency=agency)
    
    # Pagination
    paginator = Paginator(subaccounts, 10)  # Show 10 subaccounts per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'agency/subaccount_list.html', {
        'agency': agency,
        'page_obj': page_obj,
    })
