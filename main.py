import requests
import json
import schedule
import time
from datetime import datetime, timedelta

# Configurable parameters
GRAPHQL_URL = "https://api.producthunt.com/v2/api/graphql"
BEARER_TOKEN = "" 
CHECK_INTERVAL_MINUTES = 3
CHECK_INTERVAL_MULTIPLIER_BACKDATE = 5
SLACK_WEBHOOK_URL = ""
ENABLE_SLACK = True
RUN_ONCE = False
FLAGGED_COMMENT_IDS = [""] # ID's of any comments to leave "on read"

# GraphQL query
graphql_query = {
    "query": """
    {
        post(slug: "neurelo") {
            comments(first: 1000, order: NEWEST) {
                totalCount
                nodes {
                    replies {
                        totalCount
                    }
                    url
                    createdAt
                    id
                }
            }
        }
    }
    """
}

def send_slack_notification(urls):
    message = "\n".join(urls)
    payload = {
        "text": f"Found {len(urls)} comments with 0 replies in the last {CHECK_INTERVAL_MINUTES} minutes:\n{message}"
    }
    if ENABLE_SLACK:
        requests.post(SLACK_WEBHOOK_URL, json=payload)

    if RUN_ONCE:
        print(payload)

def parse_response_and_notify(response):
    data = response.json().get('data', {}).get('post', {}).get('comments', {}).get('nodes', [])
    urls_to_notify = []
    current_time = datetime.utcnow()

    for comment in data:
        created_at = datetime.strptime(comment['createdAt'], "%Y-%m-%dT%H:%M:%SZ")
        if comment['replies']['totalCount'] == 0 and current_time - created_at <= timedelta(minutes=CHECK_INTERVAL_MINUTES * CHECK_INTERVAL_MULTIPLIER_BACKDATE):
            if comment['id'] not in FLAGGED_COMMENT_IDS:
                urls_to_notify.append(comment['url'])

    if len(urls_to_notify) == 0: 
        print(f"No new comments at: {datetime.utcnow()}")

    if urls_to_notify:
        send_slack_notification(urls_to_notify)

def execute_graphql_request():
    headers = {
        "Authorization": f"Bearer {BEARER_TOKEN}",
        "Content-Type": "application/json",
        "Accept": "*/*"
    }
    response = requests.post(GRAPHQL_URL, headers=headers, json=graphql_query)
    if response.status_code == 200:
        parse_response_and_notify(response)
    else:
        print(f"Failed to execute GraphQL request. Status code: {response.status_code}")

if RUN_ONCE: 
    execute_graphql_request()

else: 
    # Schedule the task
    schedule.every(CHECK_INTERVAL_MINUTES).minutes.do(execute_graphql_request)

    # Main loop
    while True:
        schedule.run_pending()
        time.sleep(1)
