import os
import shutil
import datetime
from jinja2 import Environment, FileSystemLoader, select_autoescape

THIS_DIR = os.path.dirname(os.path.abspath(__file__))
env = Environment(
    loader=FileSystemLoader(THIS_DIR + '/templates/public'),
    trim_blocks=True,
    autoescape=select_autoescape(['html', 'xml'])
)

class Group:
    def __init__(self, heading, entries):
        self.heading = heading
        self.entries = entries

class Entry:
    def __init__(self, name, publickey, fingerprint):
        self.name = name
        self.publickey = publickey
        self.fingerprint = fingerprint

def render_page(groups):
    root_template = env.get_template('pgp-listing.html')

    date = datetime.date.today().strftime("%d, %b %Y")
    return root_template.render(groups=groups)

groups = [
    Group('B', [
        Entry('David Blishen', 'blishen pk', 'A820 60D2 AA7F E79C 98B7  43A1 A287 2CF2 263E 3238'),
        Entry('Michael Barton', 'barton pk', '578E D4D8 23DE 6042 D189  A0DB 6AC4 9BE0 7B37 BC8C')
    ]),
    Group('C', [
        Entry('Sam Cutler', 'cutler pk', '5A83 E099 6D3A B407 52C1  CF5F B553 86B7 867B A22B')
    ]),
    Group('W', [
        Entry('Kate Whalen', 'whalen pk', '6FD2 E4C9 71AD B9BB 1573  85EA 383B C341 85FB BD09')
    ])
]

if __name__ == '__main__':
    if os.path.exists('./build'):
        print('removing old build file')
        shutil.rmtree('./build')

    print('copying static assets')
    shutil.copytree('./static', './build')

    print('Creating templates')
    text_file = open("build/index.html", "w")
    text_file.write(render_page(groups))
    text_file.close()

    print('Done!')