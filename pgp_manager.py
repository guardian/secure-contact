import boto3
import os
import json

class Entry:
    def __init__(self, name, publickey, fingerprint):
        self.name = name
        self.publickey = publickey
        self.fingerprint = fingerprint

    def __str__(self):
        return f'{str(self.__class__)}: {str(self.__dict__)}'

def parse_name(key: str) -> str:
    return key.replace('PublicKeys/', '').replace('.pub.txt', '')

def fetch_fingerprint(s3_client, bucket: str, name: str) -> str:
    key = f'Fingerprints/{name}.fpr.txt'
    s3_obj = s3_client.get_object(Bucket=bucket, Key=key)
    return s3_obj['Body'].read()

def generate_entry(s3_client, bucket: str, key: str) -> Entry:
    s3_obj = s3_client.get_object(Bucket=bucket, Key=key)
    contact_name = parse_name(key)
    key_contents = s3_obj['Body'].read()
    fingerprint_contents = fetch_fingerprint(s3_client, bucket, contact_name)
    return Entry(contact_name, key_contents, fingerprint_contents)

def create_s3_client(profile):
    session = boto3.Session(profile_name=profile)
    return session.client('s3')

def get_matching_s3_objects(s3_client, bucket: str, prefix: str):
    kwargs = {'Bucket': bucket}

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

def get_matching_s3_keys(s3_client, bucket: str, prefix: str):
    for obj in get_matching_s3_objects(s3_client, bucket, prefix):
        yield obj['Key']

def main():
    config_path = os.path.expanduser('~/.gu/secure-contact.json')
    config = json.load(open(config_path))

    BUCKET_NAME = config['BUCKET_NAME']
    AWS_PROFILE = config['AWS_PROFILE']

    client = create_s3_client(AWS_PROFILE)
    public_keys = list(get_matching_s3_keys(client, BUCKET_NAME, 'PublicKeys'))
    all_entries = [generate_entry(client, BUCKET_NAME, key) for key in public_keys]

    print([str(entry) for entry in all_entries])

if __name__== "__main__":
    main()