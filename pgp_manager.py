import boto3, os, json

from typing import Dict, List, Any, Union
from boto3 import Session
from botocore.exceptions import ClientError


class Entry:
    def __init__(self, name, publickey, fingerprint):
        self.name = name
        self.publickey = publickey
        self.fingerprint = fingerprint

    def __str__(self):
        return f'{str(self.__class__)}: {str(self.__dict__)}'

    def __eq__(self, other):
        if not isinstance(other, Entry):
            return NotImplemented

        return self.name == other.name and self.publickey == other.publickey and self.fingerprint == other.fingerprint

    def __hash__(self):
        # Make class instances usable as items in hashable collections
        return hash((self.name, self.publickey, self.fingerprint))


# assumes the uploaded public key is named after the contact
def parse_name(key: str) -> str:
    return key.replace('PublicKeys/', '').replace('.pub.txt', '')


# Not all public keys will have a corresponding fingerprint
def fetch_fingerprint(s3_client, bucket: str, name: str) -> Union[None, str]:
    key = f'Fingerprints/{name}.fpr.txt'
    try:
        s3_obj = s3_client.get_object(Bucket=bucket, Key=key)
        return str(s3_obj['Body'].read())
    except ClientError as e:
        if e.response['Error']['Code'] == 'NoSuchKey':
            log = json.dumps({
                'app': 'secure-contact',
                'function': 'fetch_fingerprint',
                'message': f'NoSuchKey: {key}'
            })
            print(log)
        else:
            raise e


def generate_entry(s3_client, bucket: str, key: str) -> Entry:
    contact_name = parse_name(key)
    fingerprint = fetch_fingerprint(s3_client, bucket, contact_name)
    return Entry(contact_name, key, fingerprint)


def create_session(profile=None) -> Session:
    return boto3.Session(profile_name=profile)


def get_matching_s3_objects(s3_client, bucket: str, prefix: str) -> List[Dict[str, Any]]:
    kwargs = {'Bucket': bucket, 'Prefix': prefix, 'StartAfter': prefix}

    while True:
        # The S3 API response is a large blob of metadata.
        # 'Contents' contains information about the listed objects.
        resp = s3_client.list_objects_v2(**kwargs)

        try:
            contents = resp['Contents']
        except KeyError:
            return

        for obj in contents:
            key = obj['Key']
            if key.startswith(prefix):
                yield obj

        # The S3 API is paginated, returning up to 1000 keys at a time.
        # Pass the continuation token into the next response, until we
        # reach the final page (where this field will be missing).
        try:
            kwargs['ContinuationToken'] = resp['NextContinuationToken']
        except KeyError:
            break


def get_matching_s3_keys(s3_client, bucket: str, prefix: str) -> List[str]:
    for obj in get_matching_s3_objects(s3_client, bucket, prefix):
        yield obj['Key']


def should_be_public(entry: Entry) -> bool:
    if '.pub.txt' not in entry.publickey:
        print(f'WARNING: should_be_public check did not pass for {entry.publickey}')
        return False
    return True


# should copy a list of s3 objects from one bucket to another, preserving the directory structure
def copy_keys_to_public_bucket(session: Session, source_bucket: str, dest_bucket: str, entries: List[Entry]) -> None:
    # could we set a lifecycle on the bucket to deal with old keys?
    client = session.client('s3')
    for entry in entries:
        if should_be_public(entry):
            copy_source = {
                'Bucket': source_bucket,
                'Key': entry.publickey
            }
            client.copy(copy_source, dest_bucket, entry.publickey)


def get_content_type(filename: str) -> str:
    if filename.endswith('.html'):
        return 'text/html'
    if filename.endswith('.css'):
        return 'text/css'
    if filename.endswith('.ico'):
        return 'image/x-icon'
    else:
        return ''


def upload_html(session: Session, bucket: str, key: str, body: str) -> None:
    client = session.client('s3')
    content_type = 'text/html'
    client.put_object(Body=body, Bucket=bucket, Key=key, ContentType=content_type)


def upload_files(session: Session, bucket: str, path: str, prefix: str = '') -> None:
    client = session.client('s3')
    for subdir, dirs, files in os.walk(path):
        for file in files:
            content_type = get_content_type(file)
            full_path = os.path.join(subdir, file)
            s3path = prefix + file
            client.upload_file(full_path, bucket, s3path, ExtraArgs={'ContentType': content_type})


# fetch all of the required data from S3 and return a List containing an Entry for each contact
def get_all_entries(session: Session, data_bucket: str) -> List[Entry]:
    client = session.client('s3')
    public_keys = list(get_matching_s3_keys(client, data_bucket, 'PublicKeys/'))
    return [generate_entry(client, data_bucket, key) for key in public_keys]


if __name__ == "__main__":

    if os.getenv('STAGE'):
        DATA_BUCKET_NAME = os.getenv('DATA_BUCKET_NAME')
        PUBLIC_BUCKET_NAME = os.getenv('PUBLIC_BUCKET_NAME')
        AWS_PROFILE = os.getenv('AWS_PROFILE')
    else:
        config_path = os.path.expanduser('~/.gu/secure-contact.json')
        config = json.load(open(config_path))
        DATA_BUCKET_NAME = config['DATA_BUCKET_NAME']
        PUBLIC_BUCKET_NAME = config['PUBLIC_BUCKET_NAME']
        AWS_PROFILE = config['AWS_PROFILE']

