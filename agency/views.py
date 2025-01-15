from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.contrib import messages
from agency.forms import SubaccountForm
from django.core.paginator import Paginator
from django.contrib.auth import login

from agency.models import AccountSwitchLog, User

@login_required
def add_subaccount(request):
    # Ensure only agencies can access this view
    if not request.user.is_agency():
        messages.error(request, "You are not authorized to create subaccounts.")
        return redirect('agent:dashboards')

    if request.method == 'POST':
        form = SubaccountForm(request.POST)
        if form.is_valid():
            form.save(parent_agency=request.user)  # Save subaccount with the parent agency
            messages.success(request, "Subaccount created successfully.")
            return redirect('agency:list_subaccounts')  # Redirect to the list of subaccounts
    else:
        form = SubaccountForm()

    return render(request, 'agency/create_subaccount.html', {'form': form})


@login_required
def subaccount_list(request):
    if not request.user.is_agency():
        messages.error(request, "You are not authorized to view subaccounts.")
        return redirect('agent:dashboards')
    subaccounts = request.user.sub_accounts.all().select_related('subaccountprofile')
    # Paginate the subaccounts list
    paginator = Paginator(subaccounts, 10)  # Show 10 subaccounts per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'agency/subaccount_list.html', {'page_obj': page_obj})

@login_required
def switch_account(request, subaccount_id):
    # Ensure the logged-in user is an agency
    if not request.user.is_agency():
        messages.error(request, "You are not authorized to switch to a subaccount.")
        return redirect('agent:dashboards')
    
    # Try to get the subaccount by ID
    try:
        subaccount = User.objects.get(id=subaccount_id, user_type='sub_account')
    except User.DoesNotExist:
        messages.error(request, "The selected sub-account does not exist.")
        return redirect('agent:dashboards')

    # Log the switch in the AccountSwitchLog
    AccountSwitchLog.objects.create(agency=request.user, switched_to=subaccount)

    # Update the session or context to reflect the switch (set sub-account as the active user)
    request.session['switched_to_subaccount'] = subaccount.id
    login(request, subaccount)

    messages.success(request, f"Successfully switched to sub-account: {subaccount.username}")
    return redirect('agent:dashboards')


# from django.shortcuts import render, redirect
# from django.contrib.auth.decorators import login_required,permission_required
# from .models import Agency, Subaccount, Role, Configuration
# from .forms import SubaccountForm, ConfigurationForm
# from django.core.paginator import Paginator

# # Create a new subaccount
# @login_required
# def create_subaccount(request):
#     agency = Agency.objects.get(user=request.user)
    
#     if request.method == "POST":
#         form = SubaccountForm(request.POST)
#         if form.is_valid():
#             subaccount = form.save(commit=False)
#             subaccount.agency = agency
#             subaccount.save()
#             # Create default configuration for the subaccount
#             Configuration.objects.create(subaccount=subaccount)
#             return redirect('configure_subaccount', subaccount_id=subaccount.id)
#     else:
#         form = SubaccountForm()

#     return render(request, 'agency/create_subaccount.html', {'form': form, 'agency': agency})

# # Configure a subaccount's settings (CRM, Automations)
# @login_required
# def configure_subaccount(request, subaccount_id):
#     subaccount = Subaccount.objects.get(id=subaccount_id)
#     configuration = subaccount.configuration
    
#     if request.method == "POST":
#         form = ConfigurationForm(request.POST, instance=configuration)
#         subaccount_form = SubaccountForm(request.POST, instance=subaccount)
#         if form.is_valid() and subaccount_form.is_valid():
#             form.save()
#             subaccount_form.save()
#             return redirect('subaccount_dashboard', subaccount_id=subaccount.id)
#     else:
#         form = ConfigurationForm(instance=configuration)
#         subaccount_form = SubaccountForm(instance=subaccount)

#     return render(request, 'agency/configure_subaccount.html', {'form': form,'subaccount_form':subaccount_form, 'subaccount': subaccount})

# def list_subaccounts(request):
#     try:
#         agency = Agency.objects.get(user=request.user)
#     except Agency.DoesNotExist:
#         agency = None

#     subaccounts = Subaccount.objects.filter(agency=agency)
    
#     # Pagination
#     paginator = Paginator(subaccounts, 10)  # Show 10 subaccounts per page
#     page_number = request.GET.get('page')
#     page_obj = paginator.get_page(page_number)

#     return render(request, 'agency/subaccount_list.html', {
#         'agency': agency,
#         'page_obj': page_obj,
#     })
# @permission_required('app_name.can_manage_sub_accounts')
# def manage_sub_accounts(request):
#     # Logic for managing sub-accounts
#     return render(request, 'manage_sub_accounts.html')