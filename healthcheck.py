import requests, logging, time

from boto3 import Session
from botocore.exceptions import ClientError
from requests.exceptions import RequestException

from typing import Optional


CHARSET = "UTF-8"


def create_session(profile=None) -> Session:
    return Session(profile_name=profile)


def fetch_parameter(client, name: str) -> str:
    response = client.get_parameter(Name=name, WithDecryption=True)
    return response['Parameter']['Value']


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


def send_email(client):
    email_message = create_message('SecureDrop Status Update', 'Please update the page!')
    sender = f'Sender Name <{fetch_parameter(client, "prodmon-sender")}>'
    recipient = fetch_parameter(client, "prodmon-recipient")
    try:
        response = client.send_email(
            Destination={
                'ToAddresses': [
                    recipient,
                ],
            },
            Message=email_message,
            Source=sender,
        )
    # Display an error if something goes wrong.
    except ClientError as e:
        print(e.response['Error']['Message'])
    else:
        print("Email sent! Message ID:"),
        print(response['MessageId'])


# N.B. this script requires Tor to be running on the server
def send_request() -> Optional[requests.Response]:
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
        return requests.get('http://33y6fjyhs3phzfjj.onion', headers=headers, proxies=proxies, timeout=10)
    except RequestException as err:
        print(err)


def passes_healthcheck(response: Optional[requests.Response]) -> bool:
    expected_text = 'SecureDrop | Protecting Journalists and Sources'
    if response:
        print(f'response status code: {response.status_code}')
        if response.status_code == 200 and expected_text in response.text:
            return True
    return False


def main():
    attempts = 0
    while attempts < 5:
        attempts += 1
        response = send_request()
        if passes_healthcheck(response):
            break
        print(f'unable to reach site on attempt {attempts}')
        time.sleep(60)
    else:
        # TODO: Send an email via SNS
        pass


if __name__ == '__main__':
    main()
