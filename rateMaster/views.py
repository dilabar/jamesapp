import stripe
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings

from agent.api_view import calculate_bill
from agent.models import PhoneCall
from rateMaster.forms import MonthYearSelectionForm
from rateMaster.models import Bill

# Set your Stripe API key
stripe.api_key = settings.STRIPE_SECRET_KEY  # You can set your secret key in Django settings

@csrf_exempt  # Optionally you can use csrf_exempt to bypass CSRF validation for this request
def create_checkout_session(request):
    if request.method == 'POST':
        # Get the amount from the form (it's passed as hidden input field)
        amount = int(float(request.POST.get('amount', 0)) * 100)  # Convert to cents (e.g., 10.00 -> 1000 cents)
        
        try:
            # Create Stripe checkout session
            session = stripe.checkout.Session.create(
                payment_method_types=['card'],
                line_items=[
                    {
                        'price_data': {
                            'currency': 'usd',
                            'product_data': {
                                'name': 'Billing Payment',
                            },
                            'unit_amount': amount,
                        },
                        'quantity': 1,
                    },
                ],
                mode='payment',
                success_url=request.build_absolute_uri('/ratemaster/payment-success/') + '?session_id={CHECKOUT_SESSION_ID}',
                cancel_url=request.build_absolute_uri('/ratemaster/payment-cancel/'),
            )

            # Redirect to Stripe checkout
            return redirect(session.url)
        except stripe.error.StripeError as e:
            return JsonResponse({'error': str(e)}, status=400)

    return JsonResponse({'error': 'Invalid request'}, status=400)

def payment_success(request):
    session_id = request.GET.get('session_id')
    if session_id:
        try:
            # Optionally, you can retrieve the session details from Stripe if you want to confirm payment
            session = stripe.checkout.Session.retrieve(session_id)
            total_amount=session.amount_total / 100
            # You can use the session object to display details like product, amount, etc.
            return render(request, 'bill/payment_success.html', {'session': session,'total_amount':total_amount})
        except stripe.error.StripeError as e:
            # Handle errors if session cannot be retrieved
            return render(request, 'bill/payment_cancel.html', {'error': str(e)})
    return render(request, 'bill/payment_success.html')

def payment_cancel(request):
    return render(request, 'bill/payment_cancel.html')

def view_bill(request):
    user = request.user  # Get the user by ID

    if request.method == 'POST':
        form = MonthYearSelectionForm(request.POST)
        if form.is_valid():
            # Get the selected month as a numeric value
            selected_month = form.cleaned_data['month']
            selected_year = form.cleaned_data['year']

            # Get or create the Bill for the user and the selected month
            bill, created = Bill.objects.get_or_create(user=user, month=selected_month,year=selected_year)

            # Calculate the total bill for the user
            phone_calls = PhoneCall.objects.filter(user=user, timestamp__month=selected_month,timestamp__year=selected_year)
            total_cost = 0
            for call in phone_calls:
                total_cost += calculate_bill(call)  # Sum the bill for each call

            # Update and save the total bill in the Bill model
            bill.total_amount = round(total_cost, 2)
            bill.save()  # Save the updated bill with the new total amount

            # Render the page with the calculated bill
            return render(request, 'bill/bill_page.html', {
                'form': form,
                'user': user,
                'bill': bill,
                'selected_month': selected_month,
                'selected_year': selected_year
            })
    else:
        form = MonthYearSelectionForm()

    return render(request, 'bill/bill_page.html', {'form': form, 'user': user})

