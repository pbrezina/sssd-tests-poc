from __future__ import annotations

from ..host import BaseHost
from .base import MultihostUtility


class HostAuthselect(MultihostUtility):
    """
    Use authselect to configure nsswitch and PAM.

    All changes are automatically reverted when a test is finished.
    """

    def __init__(self, host: BaseHost) -> None:
        """
        :param host: Remote host instance.
        :type host: BaseHost
        """
        super().__init__(host)
        self.__backup: str = None

    def teardown(self):
        """
        Revert to original state.

        :meta private:
        """
        if self.__backup is not None:
            self.host.exec(['authselect', 'backup-restore', self.__backup])
            self.host.exec(['rm', '-fr', f'/var/lib/authselect/backups/{self.__backup}'])
            self.__backup = None

        super().teardown()

    def select(self, profile: str, features:  list[str]) -> None:
        backup = []
        if self.__backup is None:
            self.__backup = 'multihost.backup'
            backup = [f'--backup={self.__backup}']

        self.host.exec(['authselect', 'select', profile, *features, '--force', *backup])
