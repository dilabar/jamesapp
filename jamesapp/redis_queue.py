# utils/redis_queue.py
import redis
import json

redis_client = redis.Redis(host='localhost', port=6379, db=0)
REDIS_QUEUE_KEY = 'campaign_task_queue'

def enqueue_campaign_task(campaign_id, user_id, agent_id):
    data = {
        'campaign_id': campaign_id,
        'user_id': user_id,
        'agent_id': agent_id
    }
    redis_client.rpush(REDIS_QUEUE_KEY, json.dumps(data))

def dequeue_campaign_task():
    item = redis_client.lpop(REDIS_QUEUE_KEY)
    if item:
        return json.loads(item)
    return None
