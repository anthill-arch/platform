from anthill.framework.conf import settings
from anthill.framework.utils.asynchronous import as_future
from anthill.platform.services.update.backends.base import BaseUpdateManager
from anthill.platform.utils.ssh import PrivateSSHKeyContext
from typing import List, Optional
from git.exc import InvalidGitRepositoryError, NoSuchPathError
import git
import contextlib
import logging


logger = logging.getLogger('anthill.application')


class GitUpdateManager(BaseUpdateManager):
    local_branch = 'master'
    remote_branch = 'origin/master'
    deployment_key_file = None
    deployment_key_data = None

    def __init__(self):
        self._root = settings.BASE_DIR
        try:
            self.repo = git.Repo(self._root)
            logger.info('Git updates manager enabled.')
        except (InvalidGitRepositoryError, NoSuchPathError):
            logger.exception('Git repository appears to have an invalid format '
                             'or path does not exist.')
            self.repo = None

    def deploy_environment_context(self):
        with PrivateSSHKeyContext(self.deployment_key_data) as key_file:
            deployment_key_file = key_file or self.deployment_key_file
            if deployment_key_file:
                ssh_cmd = 'ssh -i {0}'.format(deployment_key_file)
                return self.repo.git.custom_environment(GIT_SSH_COMMAND=ssh_cmd)
            return contextlib.suppress()

    def _versions(self, branch, max_count=False) -> List[str]:
        commits = list(self.repo.iter_commits(branch, max_count=max_count))
        return list(map(lambda x: x.hexsha, commits))

    def _remote_versions(self) -> List[str]:
        return self._versions(self.remote_branch)

    remote_versions = as_future(_remote_versions)
    versions = remote_versions

    def format_version(self, value):
        return value[:7]

    def _local_versions(self) -> List[str]:
        return self._versions(self.local_branch)

    local_versions = as_future(_local_versions)

    @as_future
    def current_version(self) -> str:
        self.repo.git.checkout(self.local_branch)
        ver = self.repo.head.commit.hexsha
        return self.format_version(ver)

    @as_future
    def latest_version(self) -> str:
        with self.deploy_environment_context():
            self.repo.remotes.origin.fetch()
        remote_latest = self.repo.commit(self.remote_branch)
        ver = remote_latest.hexsha
        return self.format_version(ver)

    @as_future
    def has_updates(self) -> bool:
        local_latest = self.repo.commit(self.local_branch)
        remote_latest = self.repo.commit(self.remote_branch)
        return (local_latest != remote_latest and
                local_latest.committed_date < remote_latest.committed_date)

    @as_future
    def check_updates(self) -> List[str]:
        self.repo.git.checkout(self.local_branch)
        with self.deploy_environment_context():
            self.repo.remotes.origin.fetch()
        local_versions = set(self._local_versions())
        remote_versions = set(self._remote_versions())
        new_versions = remote_versions.difference(local_versions)
        return list(map(self.format_version, new_versions))

    @as_future
    def update(self, version: Optional[str] = None) -> None:
        self.repo.git.checkout(self.local_branch)
        with self.deploy_environment_context():
            self.repo.remote().pull()
        self.repo.git.checkout(version)
