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
    return root_template.render(groups = groups)

groups = [
    Group('B', [
        Entry('David Blishen', 'blishen pk', 'blishen fp'),
        Entry('Michael Barton', 'barton pk', 'barton fp')
    ]),
    Group('C', [
        Entry('Sam Cutler', 'cutler pk', 'cutler fp')
    ]),
    Group('W', [
        Entry('Kate Whalen', 'whalen pk', 'whalen fp')
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