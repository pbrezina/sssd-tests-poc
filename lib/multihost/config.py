from __future__ import annotations

import logging

import pytest_multihost

from .host import ADHost, BaseHost, IPAHost, LDAPHost, SambaHost


class MultihostDomain(pytest_multihost.config.Domain):
    """
    Multihost domain class.
    """

    def get_host_class(self, host_dict: dict[str, any]):
        """
        Find desired host class by role.

        :param host_dict: Host configuration as a dictionary.
        :type host_dict: dict[str, any]
        :return: Host class.
        :rtype: class
        """
        role = host_dict['role']
        if role in self.host_classes:
            return self.host_classes[role]

        return BaseHost

    @property
    def host_classes(self):
        """
        Map role to host class.

        :rtype: Class name.
        """

        return {
            'ad': ADHost,
            'ldap': LDAPHost,
            'ipa': IPAHost,
            'samba': SambaHost,
        }


class MultihostConfig(pytest_multihost.config.Config):
    """
    Low-level multihost configuration object, tight to ``pytest_multihost``
    plugin.
    """

    extra_init_args = {'log_path'}

    def __init__(self, log_path: str = None, **kwargs) -> None:
        self.log_path = log_path
        super().__init__(**kwargs)

    def get_domain_class(self):
        return MultihostDomain

    def get_logger(self, name: str) -> logging.Logger:
        """
        Get logger.
        """

        logger = logging.getLogger(name)
        if logger.hasHandlers():
            return logger

        if self.log_path is None:
            return logger

        handler = logging.FileHandler(self.log_path)
        handler.setLevel(logging.DEBUG)
        handler.setFormatter(logging.Formatter('%(name)s - %(levelname)s - %(message)s'))

        logger.addHandler(handler)
        logger.setLevel(logging.DEBUG)

        return logger
