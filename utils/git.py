from anthill.framework.utils.asynchronous import as_future
from anthill.platform.utils.ssh import PrivateSSHKeyContext


class Project:
    repo_dir = 'repo.git'
    builds_dir = 'builds'

    def __init__(self, branch_name):
        self.branch_name = branch_name

    @as_future
    def build(self, commit):
        pass

    @as_future
    def get_commits(self, amount=20):
        return self.repo.iter_commits(self.branch_name, max_count=amount)


class ProjectBuild:
    pass
