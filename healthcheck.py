import time
import os
import json
from typing import Optional, Union, Dict, List

import requests
from boto3 import Session
from botocore.exceptions import ClientError
from requests.exceptions import RequestException

METADATA_SERVICE = "http://169.254.169.254/latest/meta-data/"
CHARSET = "UTF-8"


def create_session(profile=None, region='eu-west-1') -> Session:
    return Session(profile_name=profile, region_name=region)


def fetch_parameter(client, name: str) -> Union[str, None]:
    try:
        response = client.get_parameter(Name=name, WithDecryption=True)
        return response['Parameter']['Value']
    except client.exceptions.ParameterNotFound:
        print(f'parameter not found: {name}')
        return None


def generate_text(heading: str, text: str) -> str:
    return f"""
    {heading}\r\n
    {text}\n
    This email was sent by the Secure Contact application
    """


def generate_html(heading: str, text: str) -> str:
    return f"""<html>
    <head></head>
    <body>
    <h1>{heading}</h1>
    <p>{text}</p>
    <p>This email was sent by the Secure Contact application <a href='https://aws.amazon.com/ses/'>AWS SES</a></p>
    </body>
    </html>"""


def create_message(heading: str, text: str):
    body_html = generate_html(heading, text)
    body_text = generate_text(heading, text)
    return {
        'Body': {
            'Html': {
                'Charset': CHARSET,
                'Data': body_html,
            },
            'Text': {
                'Charset': CHARSET,
                'Data': body_text,
            },
        },
        'Subject': {
            'Charset': CHARSET,
            'Data': '[ALERT P1] SecureDrop Site Failing Healthcheck',
        },
    }


def send_email(session: Session, message: Dict):
    ssm_client = session.client('ssm')
    ses_client = session.client('ses')
    sender = f'Sender Name <{fetch_parameter(ssm_client, "prodmon-sender")}>'
    recipient = fetch_parameter(ssm_client, "prodmon-recipient")
    try:
        response = ses_client.send_email(
            Destination={
                'ToAddresses': [
                    recipient,
                ],
            },
            Message=message,
            Source=sender,
        )
    # Display an error if something goes wrong.
    except ClientError as e:
        print(e.response['Error']['Message'])
    else:
        print('Email sent! Message ID:')
        print(response['MessageId'])


def send_message(session: Session):
    ssm_client = session.client('ssm')
    url = fetch_parameter(ssm_client, "prodmon-webhook")
    headers = {'Content-Type': 'application/json; charset=UTF-8'}
    message = json.dumps({'text': 'HelloWorld!'})

    try:
        response = requests.post(url=url, headers=headers, data=message)
        print(f'Got {response.status_code} from chat.googleapis.com')
    except RequestException as err:
        print(err)


# N.B. this script requires Tor to be running on the server
def send_request(session: Session) -> Optional[requests.Response]:
    client = session.client('ssm')
    target = f'http://{fetch_parameter(client, "securedrop-url")}'

    # TODO: handle any ConnectionRefusedError and ConnectTimeoutError
    headers = {
        'User-agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:52.0) Gecko/20100101 Firefox/52.0',
        'referer': 'https://www.google.com'
    }
    proxies = {
        'http': 'socks5h://127.0.0.1:9050',
        'https': 'socks5h://127.0.0.1:9050'
    }
    try:
        return requests.get(target, headers=headers, proxies=proxies, timeout=10)
    except RequestException as err:
        print(err)


def healthcheck(response: Optional[requests.Response]) -> bool:
    expected_text = 'SecureDrop | Protecting Journalists and Sources'
    if response:
        print(f'response status code: {response.status_code}')
        if response.status_code == 200 and expected_text in response.text:
            return True
    return False


def update_website_configuration(session: Session, bucket_name: str, passes_healthcheck: bool):
    suffix = 'index.html' if passes_healthcheck else 'maintenance.html'
    configuration = {
        'ErrorDocument': {'Key': 'error.html'},
        'IndexDocument': {'Suffix': suffix},
    }
    s3_client = session.client('s3')
    s3_client.put_bucket_website(Bucket=bucket_name, WebsiteConfiguration=configuration)


def run(session: Session, bucket_name: str):
    attempts = 0
    while attempts < 5:
        attempts += 1
        response = send_request(session)
        if healthcheck(response):
            print(f'Healthcheck: passed on attempt {attempts}')
            update_website_configuration(session, bucket_name, passes_healthcheck=True)
            break
        print(f'Healthcheck: unable to reach site on attempt {attempts}')
        time.sleep(60)
    else:
        email_message = create_message('SecureDrop Status Update', 'Please update the page!')
        send_email(session, email_message)
        update_website_configuration(session, bucket_name, passes_healthcheck=False)
        print('Healthcheck: failed healthcheck')
    # message the alerts channel either way to let us know the current status
    send_message(session)


if __name__ == '__main__':
    stage = os.getenv('STAGE') if os.getenv('STAGE') else 'DEV'
    aws_profile = os.getenv('AWS_PROFILE') if os.getenv('AWS_PROFILE') else None
    print(f'Configuration set for stage={stage} and profile={aws_profile}')

    boto3 = create_session(profile=aws_profile)
    client = boto3.client('ssm')
    bucket = fetch_parameter(client, f'securedrop-public-bucket-{stage}')

    if bucket is not None:
        run(boto3, bucket)
