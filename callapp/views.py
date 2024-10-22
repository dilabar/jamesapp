import pandas as pd
from django.shortcuts import render
from django.http import HttpResponse
from .forms import UploadFileForm
from twilio.rest import Client

# Twilio API credentials
account_sid = 'ACe5a76e5dab8cbce42e79798dcade9e3c'
auth_token = 'b188751b8610401f5ff26148d2ddda2c'
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




def agents(request):
    
    return render(request, 'callapp/agent.html')


def agentsdetails(request):
    
    return render(request, 'callapp/agentdetails.html')
