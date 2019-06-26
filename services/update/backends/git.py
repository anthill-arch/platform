from anthill.framework.conf import settings
from anthill.framework.utils.asynchronous import as_future
from anthill.platform.services.update.backends.base import BaseUpdateManager
from anthill.platform.utils.ssh import PrivateSSHKeyContext
from git.exc import InvalidGitRepositoryError, NoSuchPathError
from typing import List, Optional
import contextlib
import logging
import functools
import git


logger = logging.getLogger('anthill.application')


def _on_failure(retval=None):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                logger.error(str(e))
                return retval
        return wrapper
    return decorator


class GitUpdateManager(BaseUpdateManager):
    local_branch = 'master'
    remote_branch = 'origin/master'
    deployment_key_file = None
    deployment_key_data = None
    commits_max_count = False

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

    def _commits(self, branch) -> List[git.Commit]:
        return self.repo.iter_commits(branch, max_count=self.commits_max_count)

    @_on_failure()
    def _versions(self, branch) -> List[str]:
        return list(map(lambda x: x.hexsha, self._commits(branch)))

    @_on_failure()
    def _remote_versions(self) -> List[str]:
        return self._versions(self.remote_branch)

    def _get_updates(self) -> List[str]:
        self.repo.git.checkout(self.local_branch)
        with self.deploy_environment_context():
            self.repo.remotes.origin.fetch()
        local_versions = set(self._local_versions())
        remote_versions = set(self._remote_versions())
        new_versions = remote_versions.difference(local_versions)
        return list(map(self.format_version, new_versions))

    remote_versions = as_future(_remote_versions)
    versions = remote_versions

    # noinspection PyMethodMayBeStatic
    def format_version(self, value):
        return value[:7]

    def _local_versions(self) -> List[str]:
        return self._versions(self.local_branch)

    local_versions = as_future(_local_versions)

    @as_future
    @_on_failure()
    def current_version(self) -> str:
        self.repo.git.checkout(self.local_branch)
        ver = self.repo.head.commit.hexsha
        return self.format_version(ver)

    @as_future
    @_on_failure()
    def latest_version(self) -> str:
        with self.deploy_environment_context():
            self.repo.remotes.origin.fetch()
        remote_latest = self.repo.commit(self.remote_branch)
        ver = remote_latest.hexsha
        return self.format_version(ver)

    @as_future
    @_on_failure()
    def has_updates(self) -> bool:
        local_latest = self.repo.commit(self.local_branch)
        remote_latest = self.repo.commit(self.remote_branch)
        return (local_latest != remote_latest and
                local_latest.committed_date < remote_latest.committed_date)

    @as_future
    @_on_failure()
    def check_updates(self) -> List[str]:
        return self._get_updates()

    @as_future
    @_on_failure()
    def updates_info(self) -> List[str]:
        return [
            c.message for c in self._commits(self.remote_branch)
            if c.hexsha in self._get_updates()
        ]

    @as_future
    @_on_failure()
    def update(self, version: Optional[str] = None) -> None:
        self.repo.git.checkout(self.local_branch)
        with self.deploy_environment_context():
            self.repo.remote().pull()
        self.repo.git.checkout(version)
