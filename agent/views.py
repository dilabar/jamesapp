import requests
from django.shortcuts import render
from django.conf import settings

from agent.models import Agent


def call_play_ai_api(request, agent_id):
    url = f"https://api.play.ai/api/v1/agents/{agent_id}"

    headers = {
        "Authorization": f"Bearer {settings.PLAY_AI_API_KEY}",
        "X-USER-ID": settings.PLAY_AI_USER_ID,
        "Accept": "application/json"
    }

    try:
        # Make the GET request
        response = requests.get(url, headers=headers)
        response.raise_for_status()  # Raise an exception for HTTP errors

        # Parse the API response as JSON
        agent_data = response.json()

        # Render the agent details in an HTML template
        return render(request, 'agent/agent_detail.html', {'agent': agent_data})

    except requests.exceptions.RequestException as e:
        return render(request, 'error.html', {'error': str(e)})
    
def agent_list(request):
    agents = Agent.objects.all()  # Fetch all agents from the database
    context={
        'agents': agents
    }
    return render(request, 'agent/agent_list.html', context)
