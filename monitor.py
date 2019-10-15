import decimal
import numbers
import os
import time
from collections.abc import Iterable, Mapping, ByteString, Set
from typing import Optional, Union, Dict

import requests
from boto3 import Session
from boto3.dynamodb.conditions import Attr
from requests.exceptions import RequestException

from notifications import create_message, send_message, send_email
from securedrop import build_pages


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


def create_service_resource(session: Session, stage: str):
    if stage != 'DEV':
        return session.resource('dynamodb')
    # Setting the endpoint creates a table in your local version of DynamoDB.
    # Before running Secure Contact you should set up the DynamoDB tables.
    return session.resource('dynamodb', endpoint_url="http://localhost:8000")


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


# For types that involve numbers, it is recommended that Decimal
# objects are used to be able to round-trip the Python type...
# We are using a lightweight serializer from author of Bloop:
# https://github.com/boto/boto3/issues/369#issuecomment-330136042
def dump_to_dynamodb(item):
    context = decimal.Context(
        Emin=-128, Emax=126, rounding=None, prec=38,
        traps=[decimal.Clamped, decimal.Overflow, decimal.Underflow]
    )

    # don't catch str/bytes with Iterable check below;
    # don't catch bool with numbers.Number
    if isinstance(item, (str, ByteString, bool)):
        return item

    # ignore inexact, rounding errors
    if isinstance(item, numbers.Number):
        return context.create_decimal(item)

    # mappings are also Iterable
    elif isinstance(item, Mapping):
        return {
            key: dump_to_dynamodb(value)
            for key, value in item.values()
        }

    # dynamodb.TypeSerializer checks isinstance(o, Set)
    # so we cannot handle this as a list
    elif isinstance(item, Set):
        return set(map(dump_to_dynamodb, item))

    # may not be a literal instance of list
    elif isinstance(item, Iterable):
        return list(map(dump_to_dynamodb, item))

    # datetime, custom object, None
    return item


def get_expiry(current_time: int) -> float:
    # There are 604800 seconds in a week
    return current_time + 604800


def create_item(current_time: int, outcome: bool) -> Dict[str, str]:
    expiration = get_expiry(current_time)
    return {
        'CheckTime': dump_to_dynamodb(current_time),
        'ExpirationTime': dump_to_dynamodb(expiration),
        'Outcome': str(outcome)
    }


def write_to_database(dynamodb, table_name: str, outcome: bool):
    # TTL attributes must be in seconds and use the epoch time format
    # Return the time in seconds since the epoch as a floating point number
    current_time = int(time.time())
    monitor_table = dynamodb.Table(table_name)
    monitor_table.put_item(Item=create_item(current_time, outcome))


def read_from_database(dynamodb, table_name: str) -> Dict[str, str]:
    table = dynamodb.Table(table_name)
    current_time = int(time.time())
    cutoff_time = current_time - 6000
    filter_expression = Attr('CheckTime').between(cutoff_time, current_time)

    response = table.scan(
        FilterExpression=filter_expression,
        Limit=10
    )
    return response


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


def send_failure_email(session: Session, config: Dict[str, str]):
    subject = '[ALERT P1] SecureDrop Site Failing Healthcheck'
    heading = 'SecureDrop Status Update'
    message = ("Monitor will attempt to update the page content. \n"
               "Please check that the update has been applied.")
    send_email(session, config, create_message(subject, heading, message))


def state_has_changed(healthy: bool, history: Dict[str, str]) -> bool:
    # TODO: compare result of latest check with previous records
    pass


def monitor(session: Session, config: Dict[str, str]):
    dynamodb = create_service_resource(session, config['STAGE'])
    response = send_request(config['SECUREDROP_URL'])

    history = read_from_database(dynamodb, config['TABLE_NAME'])
    healthy = healthcheck(response)

    print(f'Healthcheck outcome: {healthy}')

    # TODO: perform update once per day regardless and give MOTD
    if state_has_changed(healthy, history):
        upload_website_index(session, config, healthy)
        send_message(config, healthy)
        # we also send an email alert
        if not healthy:
            send_failure_email(session, config)

    # Finally, update the database with the latest result
    write_to_database(dynamodb, config['TABLE_NAME'], healthy)


def run(session: Session, config: Dict[str, str]):
    attempts = 0
    while attempts < 5:
        attempts += 1
        response = send_request(config['SECUREDROP_URL'])
        passes_healthcheck = healthcheck(response)
        if passes_healthcheck:
            print(f'Healthcheck: passed on attempt {attempts}')
            upload_website_index(session, config, passes_healthcheck)
            send_message(config, passes_healthcheck)
            break
        print(f'Healthcheck: unable to reach site on attempt {attempts}')
        time.sleep(60)
    else:
        send_message(config, passed=False)
        send_failure_email(session, config)
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
        build_pages(CONFIG['SECUREDROP_URL'], STAGE)
        run(SESSION, CONFIG)
