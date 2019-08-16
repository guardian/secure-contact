import time
import os
import json
from typing import Optional, Union, Dict

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
    <p>This email was sent by the Secure Contact application using <a href='https://aws.amazon.com/ses/'>AWS SES</a></p>
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


def send_email(session: Session, config: Dict[str, str], message: Dict):
    ses_client = session.client('ses')
    sender = config['PRODMON_SENDER']
    recipient = config['PRODMON_RECIPIENT']
    try:
        response = ses_client.send_email(
            Destination={
                'ToAddresses': [
                    recipient,
                ],
            },
            Message=message,
            Source=f'SecureDrop Monitor <{sender}>',
        )
    # Display an error if something goes wrong.
    except ClientError as e:
        print(e.response['Error']['Message'])
    else:
        print('Email sent! Message ID:')
        print(response['MessageId'])


def generate_card(title: str, subtitle: str) -> Dict:
    return {
        "cards": [
            {
                "header": {
                    "title": title,
                    "subtitle": subtitle
                }
            }
        ]
    }


def send_message(config: Dict[str, str], passed: bool):
    headers = {'Content-Type': 'application/json; charset=UTF-8'}

    status = 'Status: 💚💚💚' if passed else 'Status: 💔💔💔'
    card = json.dumps(generate_card('SecureDrop Monitor', status))

    try:
        response = requests.post(url=config['PRODMON_WEBHOOK'], headers=headers, data=card)
        print(f'Message sent to Hangouts Chat!')
        print(f'Status code {response.status_code} returned from chat.googleapis.com')
    except RequestException as err:
        print(err)


# N.B. this script requires Tor to be running on the server
def send_request(onion_address: str) -> Optional[requests.Response]:
    # TODO: handle any ConnectionRefusedError and ConnectTimeoutError
    target = f'http://{onion_address}'
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
    # TODO: this should return AWS status code so we know if the update succeeded or failed
    suffix = 'index.html' if passes_healthcheck else 'maintenance.html'
    configuration = {
        'ErrorDocument': {'Key': 'error.html'},
        'IndexDocument': {'Suffix': suffix},
    }
    s3_client = session.client('s3')
    s3_client.put_bucket_website(Bucket=bucket_name, WebsiteConfiguration=configuration)


def perform_failure_actions(session: Session, config: Dict[str, str]):
    message = ("Monitor will attempt to update the page content. \n"
               "Please check that the update has been appplied.")
    email_message = create_message('SecureDrop Status Update', message)
    send_email(session, email_message)
    send_message(config, passed=False)
    update_website_configuration(session, config['BUCKET_NAME'], passes_healthcheck=False)


def run(session: Session, config: Dict[str, str]):
    attempts = 0
    while attempts < 5:
        attempts += 1
        response = send_request(config['SECUREDROP_URL'])
        if healthcheck(response):
            print(f'Healthcheck: passed on attempt {attempts}')
            update_website_configuration(session, config['BUCKET_NAME'], passes_healthcheck=True)
            send_message(config, passed=True)
            break
        print(f'Healthcheck: unable to reach site on attempt {attempts}')
        time.sleep(60)
    else:
        perform_failure_actions(session, config)
        print('Healthcheck: failed healthcheck')


if __name__ == '__main__':
    STAGE = os.getenv('STAGE') if os.getenv('STAGE') else 'DEV'
    AWS_PROFILE = os.getenv('AWS_PROFILE') if os.getenv('AWS_PROFILE') else None
    print(f'Configuration set for stage={STAGE} and profile={AWS_PROFILE}')

    SESSION = create_session(profile=AWS_PROFILE)
    SSM_CLIENT = SESSION.client('ssm')

    CONFIG = {
        'BUCKET_NAME': fetch_parameter(SSM_CLIENT, f'/secure-contact/{STAGE}/securedrop-public-bucket'),
        'PRODMON_WEBHOOK': fetch_parameter(SSM_CLIENT, f'/secure-contact/{STAGE}/prodmon-webhook'),
        'PRODMON_SENDER': fetch_parameter(SSM_CLIENT, f'/secure-contact/{STAGE}/prodmon-sender'),
        'PRODMON_RECIPIENT': fetch_parameter(SSM_CLIENT, f'/secure-contact/{STAGE}/prodmon-recipient'),
        'SECUREDROP_URL': fetch_parameter(SSM_CLIENT, "securedrop-url")
    }

    if CONFIG['BUCKET_NAME'] is not None:
        run(SESSION, CONFIG)
