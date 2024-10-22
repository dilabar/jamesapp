import pandas as pd
from django.shortcuts import render
from django.http import HttpResponse
from .forms import UploadFileForm
from twilio.rest import Client

# Twilio API credentials
account_sid = 'AC69dfc1ab681f0938ddfc48f393598fcb'
auth_token = 'e348d1151d42ab1c33a72687344230f3'
twilio_phone_number = '+12515174099'
client = Client(account_sid, auth_token)

def upload_file(request):
    if request.method == 'POST':
        form = UploadFileForm(request.POST, request.FILES)
        if form.is_valid():
            # Read the Excel file
            file = request.FILES['file']
            df = pd.read_excel(file)

            # Make calls to the numbers in the Excel file
            for index, row in df.iterrows():
                mobile_number = row['Mobile']
                call = client.calls.create(
                    twiml='<Response><Say>Hello, this is your AI assistant!</Say></Response>',
                    to=mobile_number,
                    from_=twilio_phone_number
                )
                print(f"Call initiated to {mobile_number}, SID: {call.sid}")

            return HttpResponse("Calls initiated successfully!")
    else:
        form = UploadFileForm()
    return render(request, 'callapp/upload.html', {'form': form})
