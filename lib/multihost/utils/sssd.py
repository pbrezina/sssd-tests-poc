from __future__ import annotations

import configparser
from functools import partial
from io import StringIO
from typing import TYPE_CHECKING

from .base import MultihostUtility

if TYPE_CHECKING:
    from ..command import RemoteCommandResult
    from ..host import BaseHost, ProviderHost
    from ..roles import BaseRole
    from .fs import HostFileSystem
    from .service import HostService


class HostSSSD(MultihostUtility):
    """
    Manage SSSD on remote host.

    All changes are reverted when :func:`teardown` method is called. Teardown is
    called automatically if instance of this class is a member of
    :class:`lib.multihost.roles.BaseRole` object.
    """

    def __init__(self, host: BaseHost, fs: HostFileSystem, svc: HostService, load_config: bool = False) -> None:
        super().__init__(host)
        self.fs = fs
        self.svc = svc
        self.config = configparser.ConfigParser(interpolation=None)
        self.default_domain = None
        self.__load_config = load_config

        # Shortcuts for responders
        def create_property(name: str) -> dict[str, str]:
            return property(
                fget=partial(self.__get, name),
                fset=partial(self.__set, name),
                fdel=partial(self.__del, name)
            )

        self.autofs = create_property('autofs')
        """
        Configuration of autofs responder.
        """

        self.ifp = create_property('ifp')
        """
        Configuration of ifp responder.
        """

        self.kcm = create_property('kcm')
        """
        Configuration of kcm responder.
        """

        self.nss = create_property('nss')
        """
        Configuration of nss responder.
        """

        self.pac = create_property('pac')
        """
        Configuration of pac responder.
        """

        self.pam = create_property('pam')
        """
        Configuration of pam responder.
        """

        self.ssh = create_property('ssh')
        """
        Configuration of ssh responder.
        """

        self.sudo = create_property('sudo')
        """
        Configuration of sudo responder.
        """

    def setup(self) -> None:
        """
        :meta private:
        """

        # Disable burst limiting to allow often sssd restarts for tests
        self.fs.mkdir('/etc/systemd/system/sssd.service.d')
        self.fs.write('/etc/systemd/system/sssd.service.d/override.conf', '''
            [Unit]
            StartLimitIntervalSec=0
            StartLimitBurst=0
        ''')
        self.svc.reload_daemon()

        if self.__load_config:
            self.config_load()
            return

        # Set default configuration
        self.config.read_string('''
            [sssd]
            config_file_version = 2
            services = nss, pam
        ''')

    def start(
        self,
        service='sssd',
        raise_on_error: bool = True,
        wait: bool = True,
        apply_config: bool = True,
        check_config: bool = True
    ) -> RemoteCommandResult:
        """
        Start SSSD service.

        :param service: Service to start, defaults to 'sssd'
        :type service: str, optional
        :param raise_on_error: Raise exception on error, defaults to True
        :type raise_on_error: bool, optional
        :param wait: Wait for the command to finish, defaults to True
        :type wait: bool, optional
        :param apply_config: Apply current configuration, defaults to True
        :type apply_config: bool, optional
        :param check_config: Check configuration for typos, defaults to True
        :type check_config: bool, optional
        :return: Remote command result.
        :rtype: RemoteCommandResult
        """

        if apply_config:
            self.config_apply(check_config=check_config)

        return self.svc.start(service, raise_on_error=raise_on_error, wait=wait)

    def stop(self, service='sssd', raise_on_error: bool = True, wait: bool = True) -> RemoteCommandResult:
        """
        Stop SSSD service.

        :param service: Service to start, defaults to 'sssd'
        :type service: str, optional
        :param raise_on_error: Raise exception on error, defaults to True
        :type raise_on_error: bool, optional
        :param wait: Wait for the command to finish, defaults to True
        :type wait: bool, optional
        :return: Remote command result.
        :rtype: RemoteCommandResult
        """

        return self.svc.stop(service, raise_on_error=raise_on_error, wait=wait)

    def restart(
        self,
        service='sssd',
        raise_on_error: bool = True,
        wait: bool = True,
        apply_config: bool = True,
        check_config: bool = True
    ) -> RemoteCommandResult:
        """
        Restart SSSD service.

        :param service: Service to start, defaults to 'sssd'
        :type service: str, optional
        :param raise_on_error: Raise exception on error, defaults to True
        :type raise_on_error: bool, optional
        :param wait: Wait for the command to finish, defaults to True
        :type wait: bool, optional
        :param apply_config: Apply current configuration, defaults to True
        :type apply_config: bool, optional
        :param check_config: Check configuration for typos, defaults to True
        :type check_config: bool, optional
        :return: Remote command result.
        :rtype: RemoteCommandResult
        """
        if apply_config:
            self.config_apply(check_config=check_config)

        return self.svc.restart(service, raise_on_error=raise_on_error, wait=wait)

    def clear(self, *, db: bool = True, config: bool = False, logs: bool = False):
        """
        Clear SSSD data.

        :param db: Remove cache and database, defaults to True
        :type db: bool, optional
        :param config: Remove configuration files, defaults to False
        :type config: bool, optional
        :param logs: Remove logs, defaults to False
        :type logs: bool, optional
        """

        cmd = 'rm -fr'

        if db:
            cmd += ' /var/lib/sss/db/*'

        if config:
            cmd += ' /etc/sssd/*.conf /etc/sssd/conf.d/*'

        if logs:
            cmd += ' /var/log/sssd/*'

        self.host.exec('rm -fr /var/lib/sss/db/* /var/log/sssd/*')

    def import_domain(self, name: str, role: BaseRole) -> None:
        """
        Import SSSD domain from role object.

        :param name: SSSD domain name.
        :type name: str
        :param role: Provider role object to use for import.
        :type role: BaseRole
        :raises ValueError: If unsupported provider is given.
        """

        host = role.host

        if not isinstance(host, ProviderHost):
            raise ValueError(f'Host type {type(host)} can not be imported as domain')

        self.config[f'domain/{name}'] = host.client
        self.config['sssd'].setdefault('domains', '')

        if not self.config['sssd']['domains']:
            self.config['sssd']['domains'] = name
        elif name not in [x.strip() for x in self.config['sssd']['domains'].split(',')]:
            self.config['sssd']['domains'] += ', ' + name

        if self.default_domain is None:
            self.default_domain = name

    def config_dumps(self) -> str:
        """
        Get current SSSD configuration.

        :return: SSSD configuration.
        :rtype: str
        """

        with StringIO() as ss:
            self.config.write(ss)
            ss.seek(0)
            return ss.read()

    def config_load(self) -> None:
        """
        Load remote SSSD configuration.
        """

        result = self.host.exec(['cat', '/etc/sssd/sssd.conf'], log_stdout=False)
        self.config.clear()
        self.config.read_string(result.stdout)

    def config_apply(self, check_config: bool = True) -> None:
        """
        Apply current configuration on remote host.

        :param check_config: Check configuration for typos, defaults to True
        :type check_config: bool, optional
        """

        contents = self.config_dumps()
        self.fs.write('/etc/sssd/sssd.conf', contents, mode='0600')

        if check_config:
            self.host.exec('sssctl config-check')

    def section(self, name: str) -> dict[str, str]:
        """
        Get sssd.conf section.

        :param name: Section name.
        :type name: str
        :return: Section configuration object.
        :rtype: dict[str, str]
        """

        return self.__get(name)

    def dom(self, name: str) -> dict[str, str]:
        """
        Get sssd.conf domain section.

        :param name: Domain name.
        :type name: str
        :return: Section configuration object.
        :rtype: dict[str, str]
        """

        return self.section(f'domain/{name}')

    def subdom(self, domain: str, subdomain: str) -> dict[str, str]:
        """
        Get sssd.conf subdomain section.

        :param domain: Domain name.
        :type domain: str
        :param subdomain: Subdomain name.
        :type subdomain: str
        :return: Section configuration object.
        :rtype: dict[str, str]
        """

        return self.section(f'domain/{domain}/{subdomain}')

    @property
    def domain(self) -> dict[str, str]:
        """
        Default domain section configuration object.

        Default domain is the first domain imported by :func:`import_domain`.

        :raises ValueError: If no default domain is set.
        :return: Section configuration object.
        :rtype: dict[str, str]
        """
        if self.default_domain is None:
            raise ValueError(f'{self.__class__}.default_domain is not set')

        return self.dom(self.default_domain)

    @domain.setter
    def domain(self, value: dict[str, str]) -> None:
        if self.default_domain is None:
            raise ValueError(f'{self.__class__}.default_domain is not set')

        self.config[f'domain/{self.default_domain}'] = value

    @domain.deleter
    def domain(self, value: dict[str, str]) -> None:
        if self.default_domain is None:
            raise ValueError(f'{self.__class__}.default_domain is not set')

        del self.config[f'domain/{self.default_domain}']

    def __get(self, section: str) -> dict[str, str]:
        self.config.setdefault(section, {})
        return self.config[section]

    def __set(self, section: str, value: dict[str, str]) -> None:
        self.config[section] = value

    def __del(self, section: str) -> None:
        del self.config[section]
