import os
import shutil
import json
import pgp_manager
import re

from pgp_manager import Entry
from jinja2 import Environment, FileSystemLoader, select_autoescape
from markupsafe import Markup
from urllib import parse

from typing import Dict, List, Union


class Group:
    def __init__(self, heading, entries):
        self.heading = heading
        self.entries = entries

    def __eq__(self, other):
        if not isinstance(other, Group):
            return NotImplemented

        return self.heading == other.heading and self.entries == other.entries

    def __hash__(self):
        # Make class instances usable as items in hashable collections
        return hash((self.heading, self.entries))


class EnhancedEntry:
    def __init__(self, other_names, last_name, publickey, fingerprint, email):
        self.other_names = other_names
        self.last_name = last_name
        self.publickey = publickey
        self.fingerprint = fingerprint
        self.email = email

    def __str__(self):
        return f'{str(self.__class__)}: {str(self.__dict__)}'

    def __eq__(self, other):
        if not isinstance(other, EnhancedEntry):
            return NotImplemented

        return self.other_names == other.other_names and self.last_name == other.last_name \
            and self.publickey == other.publickey and self.fingerprint == other.fingerprint \
            and self.email == other.email

    def __hash__(self):
        # Make class instances usable as items in hashable collections
        return hash((self.other_names, self.last_name, self.publickey, self.fingerprint, self.email))


# TODO: handle nonetype better than empty string
def parse_fingerprint(raw_fingerprint: Union[None, str]) -> str:
    if isinstance(raw_fingerprint, str):
        split_str = raw_fingerprint.split('Key fingerprint = ', 1)
        if len(split_str) > 1:
            return split_str[1][:50]
        else:
            pattern = re.compile(r'([A-Z0-9]{4}\s{1,2}){9}[A-Z0-9]{4}')
            match = re.search(pattern, raw_fingerprint)
            if match:
                return match.group()
    return ''


def obscure_email(raw_email: Union[None, str]) -> str:
    # Leira is revered as the goddess of illusion in the Forgotten Realms
    obscure = '<span class="leira">leira</span>[@]<span class="leira">illusion</span>'
    if '@' in raw_email:
        return Markup(raw_email.replace('@', obscure))


def parse_email(raw_fingerprint: Union[None, str]) -> str:
    if isinstance(raw_fingerprint, str):
        if '<' in raw_fingerprint:
            return raw_fingerprint[raw_fingerprint.find('<')+1:raw_fingerprint.find('>')]
        # once we split the string, there should only be one that contains a @ symbol
        # so we can use list comprehension to find the one we want...
        email_result = [string for string in raw_fingerprint.split(' ') if '@' in string]
        # there should be exactly one result or something has gone horribly wrong...
        if len(email_result) == 1:
            # why not rstrip? Strange, there is a single edge case that is really stubborn
            # so instead we are going to find the index of the expected end of the email
            email_end = max([
                email_result[0].find('guardian.co.uk') + 14,
                email_result[0].find('guardian.com') + 12]
            )
            email = email_result[0][:email_end]
            return email
    return ''


# Names are hard and given the sample dataset, this works for the current publickeys
# https://www.kalzumeus.com/2010/06/17/falsehoods-programmers-believe-about-names/ 
def enhance_entry(entry: Entry) -> EnhancedEntry:
    other_names, last_name = entry.name.rsplit(' ', 1)
    key_url = parse.quote(entry.publickey)
    fingerprint = parse_fingerprint(entry.fingerprint)
    email = obscure_email(parse_email(entry.fingerprint))
    return EnhancedEntry(other_names, last_name, key_url, fingerprint, email)


def sort_entries(unsorted_entries: List[EnhancedEntry]) -> Dict[str, List[EnhancedEntry]]:
    alphabetical_groups = {}
    for entry in unsorted_entries:
        if len(entry.last_name) > 1:
            grouping = entry.last_name[0].upper()
            alphabetical_groups.setdefault(grouping, []).append(entry)
    return alphabetical_groups


def create_ordered_groups(groups: Dict[str, List[EnhancedEntry]]) -> List[Group]:
    alphabetical_groups = sorted(groups)
    for key in alphabetical_groups:
        entries = groups[key]
        yield Group(key, sorted(entries, key=lambda entry: entry.last_name))


THIS_DIR = os.path.dirname(os.path.abspath(__file__))
env = Environment(
    loader=FileSystemLoader(THIS_DIR + '/templates/public'),
    trim_blocks=True,
    autoescape=select_autoescape(['html', 'xml'])
)


def render_page(path: str, groups: List[Group]):
    root_template = env.get_template('pgp-listing.html')
    return root_template.render(path=path, groups=groups)


def lambda_handler(event, context) -> None:
    DATA_BUCKET_NAME = os.getenv('DATA_BUCKET_NAME')
    PUBLIC_BUCKET_NAME = os.getenv('PUBLIC_BUCKET_NAME')

    aws_session = pgp_manager.create_session()
    all_entries = pgp_manager.get_all_entries(aws_session, DATA_BUCKET_NAME)

    pgp_manager.copy_keys_to_public_bucket(aws_session, DATA_BUCKET_NAME, PUBLIC_BUCKET_NAME, all_entries)
    pgp_manager.upload_files(aws_session, PUBLIC_BUCKET_NAME, 'static/', 'static/')

    enhanced_entries = [enhance_entry(entry) for entry in all_entries]
    all_groups = create_ordered_groups(sort_entries(enhanced_entries))
    index_page = render_page('pgp/', all_groups)

    pgp_manager.upload_html(aws_session, PUBLIC_BUCKET_NAME, 'index.html', index_page)


if __name__ == '__main__':
    STAGE = os.getenv('STAGE') if os.getenv('STAGE') else 'DEV'
    config_path = os.path.expanduser('~/.gu/secure-contact.json')
    config = json.load(open(config_path))

    AWS_PROFILE = config['AWS_PROFILE']
    DATA_BUCKET_NAME = config['DATA_BUCKET_NAME']

    print(f'Using configuration for stage={STAGE} and profile={AWS_PROFILE}')

    session = pgp_manager.create_session(AWS_PROFILE)
    entries = pgp_manager.get_all_entries(session, DATA_BUCKET_NAME)

    enhanced = [enhance_entry(entry) for entry in entries]
    groups = create_ordered_groups(sort_entries(enhanced))

    if os.path.exists('./build'):
        print('Build: removing old build file')
        shutil.rmtree('./build')

    print('Build: copying static assets')
    shutil.copytree('./static', './build/static')

    print('Build: creating templates')
    text_file = open("build/index.html", "w")
    text_file.write(render_page('', groups))
    text_file.close()

    print('Build: Done!')

