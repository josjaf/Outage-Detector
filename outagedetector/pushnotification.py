from pushbullet import PushBullet, errors
import requests
import json


def push_to_iOS(title, body, pb_key):
    pb = PushBullet(pb_key)

    pb.push_note(title, body)


def push_to_ifttt(ifttt_name, api_key, notification):
    requests.post(url='https://maker.ifttt.com/trigger/{}/with/key/{}'.format(ifttt_name, api_key),
                  data={'value1': notification})


def push_to_slack(webhook_url, message):
    # Set the webhook_url to the one provided by Slack when you create the webhook at https://my.slack.com/services/new/incoming-webhook/

    slack_data = {'text': message}

    response = requests.post(
        webhook_url, data=json.dumps(slack_data),
        headers={'Content-Type': 'application/json'}
    )
    if response.status_code != 200:
        raise ValueError(
            'Request to slack returned an error %s, the response is:\n%s')
