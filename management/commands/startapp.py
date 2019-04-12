from anthill.framework.core.management.commands import StartApplication as BaseStartApplication
from urllib.parse import urlunparse
from pathlib import Path
import json
import os


def build_location(scheme='http', host='localhost', port=''):
    components = list([None] * 6)
    components[0] = scheme
    if port:
        components[1] = '%(host)s:%(port)s' % {'host': host, 'port': port}
    else:
        components[1] = host
    components[2] = ''
    return urlunparse(components)


class StartApplication(BaseStartApplication):
    name = 'startapp'

    def __init__(self, root_templates_mod=None, services_registry_file=None,
                 ui_static_path=None, ui_template_path=None):
        super().__init__(root_templates_mod)
        self.services_registry_file = services_registry_file
        self.ui_static_path = ui_static_path
        self.ui_template_path = ui_template_path

    def generate_ui_templates(self, app_name):
        def build_path(base, path_template):
            return os.path.join(base, path_template % {'app_name': app_name})
        files = [
            build_path(self.ui_template_path, 'services/%(app_name)s/index.html'),
            build_path(self.ui_static_path, 'css/pages/services/%(app_name)s.css'),
            build_path(self.ui_static_path, 'js/pages/services/%(app_name)s.js')
        ]
        for path in files:
            try:
                Path(path).touch()
            except FileNotFoundError:
                Path(os.path.dirname(path)).mkdir(mode=0o755, parents=False)
                Path(path).touch()

    def create_new_registry_entry(self, app_name, host, port):
        location = build_location('http', host, port)
        entry = {
            app_name: {"internal": location, "external": location}
        }
        with open(self.services_registry_file, "r") as f:
            data = json.load(f)
        if app_name in data:
            raise ValueError('Registry file already has this service')
        data.update(entry)
        with open(self.services_registry_file, "w") as f:
            json.dump(data, f, indent=2)

    def run(self, **options):
        app_name = options.get('name')
        host, port = options.get('host'), options.get('port')
        self.create_new_registry_entry(app_name, host, port)
        self.generate_ui_templates(app_name)
        super().run(**options)
