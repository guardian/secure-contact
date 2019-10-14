import os
import time
from typing import Optional, Union, Dict

import requests
from boto3 import Session
from requests.exceptions import RequestException

import securedrop
from notifications import create_message, send_message, send_email

CHARSET = "UTF-8"


def get_stage(filename: str) -> str:
    stage = 'DEV'
    if os.path.exists(filename):
        try:
            with open(filename) as fobj:
                stage = fobj.readline().strip()
        except IOError:
            print('cannot open', filename)
    return stage


def create_session(profile=None, region='eu-west-1') -> Session:
    return Session(profile_name=profile, region_name=region)


def fetch_parameter(client, name: str) -> Union[str, None]:
    try:
        response = client.get_parameter(Name=name, WithDecryption=True)
        return response['Parameter']['Value']
    except client.exceptions.ParameterNotFound:
        print(f'parameter not found: {name}')
        return None


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


def get_expiry(current_time: float) -> float:
    # There are 604800 seconds in a week
    return current_time + float(604800)


def write_to_database(session: Session, config: Dict[str, str], result: bool) -> None:
    client = session.client('dynamodb')
    # TTL attributes must be in seconds and use the epoch time format
    # Return the time in seconds since the epoch as a floating point number
    timestamp = time.time()
    table_name = config['TABLE_NAME']
    ttl_expiry = get_expiry(timestamp)

    client.put_item(
        TableName=config['TABLE_NAME'],
        Item={
            'timestamp': timestamp,
            'outcome': result
        }
    )


def upload_website_index(session: Session, config: Dict[str, str], passes_healthcheck: bool) -> None:
    file_name = 'build/index.html' if passes_healthcheck else 'build/maintenance.html'
    client = session.client('s3')
    client.upload_file(file_name, config['BUCKET_NAME'], 'index2.html', ExtraArgs={'ContentType': 'text/html'})


# talk to Kate to find out why this solution currently does not work for PROD >_< ...SADNESS
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
    upload_website_index(session, config, passes_healthcheck=False)


def run(session: Session, config: Dict[str, str]):
    attempts = 0
    while attempts < 5:
        attempts += 1
        response = send_request(config['SECUREDROP_URL'])
        if healthcheck(response):
            print(f'Healthcheck: passed on attempt {attempts}')
            upload_website_index(session, config, passes_healthcheck=True)
            send_message(config, passed=True)
            break
        print(f'Healthcheck: unable to reach site on attempt {attempts}')
        time.sleep(60)
    else:
        perform_failure_actions(session, config)
        print('Healthcheck: failed healthcheck')


if __name__ == '__main__':
    STAGE = get_stage('/etc/stage')
    AWS_PROFILE = 'infosec' if STAGE == 'DEV' else None
    SESSION = create_session(profile=AWS_PROFILE)
    SSM_CLIENT = SESSION.client('ssm')

    print(f'Fetching configuration for stage={STAGE} and profile={AWS_PROFILE}')

    CONFIG = {
        'BUCKET_NAME': fetch_parameter(SSM_CLIENT, f'/secure-contact/{STAGE}/securedrop-public-bucket'),
        'PRODMON_WEBHOOK': fetch_parameter(SSM_CLIENT, f'/secure-contact/{STAGE}/prodmon-webhook'),
        'PRODMON_SENDER': fetch_parameter(SSM_CLIENT, f'/secure-contact/{STAGE}/prodmon-sender'),
        'PRODMON_RECIPIENT': fetch_parameter(SSM_CLIENT, f'/secure-contact/{STAGE}/prodmon-recipient'),
        'SECUREDROP_URL': fetch_parameter(SSM_CLIENT, "securedrop-url"),
        'TABLE_NAME': f'MonitorHistory-{STAGE}'
    }

    if CONFIG['BUCKET_NAME'] is not None:
        securedrop.build_pages(CONFIG['SECUREDROP_URL'], STAGE)
        run(SESSION, CONFIG)
