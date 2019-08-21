import os
import shutil

from jinja2 import Environment, FileSystemLoader, select_autoescape


THIS_DIR = os.path.dirname(os.path.abspath(__file__))
env = Environment(
    loader=FileSystemLoader(THIS_DIR + '/templates/public'),
    trim_blocks=True,
    autoescape=select_autoescape(['html', 'xml'])
)


def render_page(securedrop_url: str, path: str, passes_healthcheck: bool):
    root_template = env.get_template('securedrop.html')
    return root_template.render(
        securedrop_url=securedrop_url,
        path=path,
        passes_healthcheck=passes_healthcheck
    )


def build_pages(securedrop_url: str, stage: str):
    # routing in Fastly requires the PROD pages to include securedrop/ before links to assets
    path = 'securedrop/' if stage == 'PROD' else ''

    if os.path.exists('./build'):
        shutil.rmtree('./build')
    os.makedirs('./build')

    passed = render_page(securedrop_url, path=path, passes_healthcheck=True)
    failed = render_page(securedrop_url, path=path, passes_healthcheck=False)

    index = open("build/index.html", "w")
    maintenance = open("build/maintenance.html", "w")

    index.write(passed)
    maintenance.write(failed)
    index.close()
    maintenance.close()


if __name__ == '__main__':
    build_pages('33y6fjyhs3phzfjj.onion', stage='DEV')
    shutil.copytree('./static', './build/static')

