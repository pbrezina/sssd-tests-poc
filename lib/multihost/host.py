from __future__ import annotations

from typing import TYPE_CHECKING

import ldap
import ldap.ldapobject
import ldap.modlist
from pytest_multihost.host import Host as pytest_multihost_Host
from pytest_multihost.transport import SSHCommand as pytest_SSHCommand

from .command import RemoteCommandResult

if TYPE_CHECKING:
    from .config import MultihostDomain


class BaseHost(object):
    """
    Base host class that provides access to the remote host.
    """

    def __init__(self, host: pytest_multihost_Host, config: dict[str, any]):
        """
        :param host: Low level pytest_multihost host instance.
        :type host: pytest_multihost.Host
        :param config: Additional configuration.
        :type config: dict[str, any]
        """
        self.host: pytest_multihost_Host = host
        self.role: str = self.host.role
        self.hostname: str = self.host.external_hostname
        self.domain = self.hostname.split('.', maxsplit=1)[1]
        self.config: dict[str, any] = config

        self.test_dir = self.host.test_dir

    @classmethod
    def from_dict(cls, dct: dict[str, any], domain: MultihostDomain) -> BaseHost:
        """
        Create host instance from a configuration in dictionary.

        This extends standard pytest_multihost configuration with additional
        field ``config`` that contains additional host specific settings.

        It also combines and renames pytest_multihost fields ``name`` and
        ``external_hostname`` with ``hostname`` to allow shorter and more
        clear definition.

        .. code-block:: yaml
            :caption: Example configuration in YAML format

            - hostname: dc.ad.test
              role: ad
              username: Administrator@ad.test
              password: vagrant
              config:
                binddn: Administrator@ad.test
                bindpw: vagrant
                client:
                  ad_domain: ad.test
                  krb5_keytab: /enrollment/ad.keytab
                  ldap_krb5_keytab: /enrollment/ad.keytab

        * Optional fields: ``ip``, ``username``, ``password``, ``config``
        * Required fields: ``hostname``, ``role``

        :param dct: Configuration as a dictionary.
        :type dct: dict[str, any]
        :param domain: Multihost domain.
        :type domain: MultihostDomain
        :raises KeyError: If required attribute is not set or if unknown attribute was provided.
        :return: Host instance.
        :rtype: BaseHost
        """
        optional = ['ip', 'username', 'password', 'config']
        required = ['hostname', 'role']

        for attr in required:
            if attr not in dct:
                raise KeyError(f'Attribute "{attr}" must be set')

        for attr in dct.keys():
            if attr not in optional + required:
                raise KeyError(f'Attribute "{attr}" is not allowed')

        # Legacy keys used by python_multihost, name is required.
        # External hostname and role is required by us.
        # Dot at the end on name prevents appending domain name to it.
        legacy = {
            'name': dct['hostname'] + '.',
            'external_hostname': dct['hostname'],
            'role': dct['role'],
            'ip': dct.get('ip', None),
            'username': dct.get('username', None),
            'password': dct.get('password', None),
        }

        host = pytest_multihost_Host.from_dict(legacy, domain)
        config = dct.get('config', {})

        return cls(host=host, config=config)

    def to_dict(self) -> dict[str, any]:
        """
        Convert this host configuration into dictionary.

        :return: Host configuration.
        :rtype: dict[str, any]
        """
        return {
            'role': self.role,
            'hostname': self.hostname,
            'ip': self.host.ip,
            'config': self.config,
        }

    def exec(
        self,
        argv: str | list[any] | tuple[any],
        *,
        cwd: str = None,
        stdin: str | bytes = None,
        env: dict[str, any] = dict(),
        log_stdout: bool = True,
        raise_on_error: bool = True,
        wait: bool = True
    ) -> RemoteCommandResult:
        """
        Execute command on remote host inside a bash shell.

        :param argv: Command or script to execute as string or argv list.
        :type argv: str | list[any] | tuple[any]
        :param cwd: Working directory where the command should be executed, defaults to None
        :type cwd: str, optional
        :param stdin: Standard input, defaults to None
        :type stdin: str | bytes, optional
        :param env: Environment variables, defaults to dict()
        :type env: dict[str, any], optional
        :param log_stdout: If True, command output is printed to the logger, defaults to True
        :type log_stdout: bool, optional
        :param raise_on_error: Raise ``subprocess.CalledProcessError`` on non-zero return code, defaults to True
        :type raise_on_error: bool, optional
        :param wait: Wait for the command to finish, defaults to True
        :type wait: bool, optional
        :raises ValueError: If argv or cwd is empty.
        :raises TypeError: If argv is instance of unsupported type.
        :return: Command result, if ``wait`` is set to False, you need to call ``res.wait()``.
        :rtype: RemoteCommandResult
        """
        if not argv:
            raise ValueError('Parameter "argv" can not be empty.')

        if not isinstance(argv, (str, list, tuple)):
            raise TypeError('Parameter "argv" can be: str, list[any], tuple[any]')

        if cwd is not None and not cwd:
            raise ValueError('Parameter "cwd" can not be empty.')

        command = self._open_shell('bash', argv, log_stdout=log_stdout, encoding='utf-8')

        def write(str: str) -> None:
            command.stdin.write(str.encode('utf-8'))

        # Set environment
        for key, value in env.items():
            value = self.__escape_argv(value)
            write(f'export {key}={value}\n')

        # Set working directory
        if cwd is not None:
            arg = self.__escape_argv(cwd)
            write(f"cd '{arg}'\n")

        # Write input data
        arg = self.__escape_echo(stdin)
        write(f"echo -en '{arg}' | ")

        argv = [argv] if isinstance(argv, (str, bytes)) else [f"'{self.__escape_argv(x)}'" for x in argv]
        write(f"( {' '.join(argv)} )\n")
        write('exit\n')
        command.stdin.flush()
        command.raiseonerr = raise_on_error

        if wait:
            command.wait()

        return RemoteCommandResult(command)

    def _open_shell(self, sh: str, argv, log_stdout=True, encoding='utf-8') -> pytest_SSHCommand:
        transport = self.host.transport
        transport.log.info('RUN %s', argv)
        return transport._run(['-o', 'LogLevel=ERROR', sh], argv=argv, log_stdout=log_stdout, encoding=encoding)

    def __decode(self, value: any) -> str:
        if isinstance(value, bytes):
            return value.decode('utf-8')

        return str(value)

    def __escape_echo(self, value: any) -> str:
        value = self.__decode(value)
        value = value.replace("\\", r"\\")
        value = value.replace("\0", r"\x00")
        value = value.replace("'", r"\'")
        return value

    def __escape_argv(self, value: any) -> str:
        return self.__decode(value).replace("'", r"\'")


class ProviderHost(BaseHost):
    """
    Generic provider host.

    Provides access to LDAP connection for direct manipulation with remote
    directory server.
    """

    def __init__(self, host: pytest_multihost_Host, config: dict[str, any], tls: bool = True):
        """
        :param host: Low level pytest_multihost host instance.
        :type host: pytest_multihost.Host
        :param config: Additional configuration.
        :type config: dict[str, any]
        :param tls: Require TLS connection, defaults to True
        :type tls: bool, optional
        """
        super().__init__(host, config)
        self.client: dict[str, any] = config.get('client', {})

        self.tls = tls
        self.uri = f'ldap://{self.hostname}'
        self.binddn = self.config.get('binddn', 'cn=Directory Manager')
        self.bindpw = self.config.get('bindpw', 'Secret123')

        # Lazy properties.
        self.__conn = None
        self.__naming_context = None

    @property
    def conn(self) -> ldap.ldapobject.LDAPObject:
        """
        LDAP connection (``python-ldap`` library).

        :rtype: ldap.ldapobject.LDAPObject
        """
        if not self.__conn:
            self.__conn = ldap.initialize(self.uri)
            self.__conn.protocol_version = ldap.VERSION3
            self.__conn.set_option(ldap.OPT_REFERRALS, 0)

            if self.tls:
                self.__conn.set_option(ldap.OPT_X_TLS_REQUIRE_CERT, ldap.OPT_X_TLS_DEMAND)
                self.__conn.start_tls_s()

            self.__conn.simple_bind_s(self.binddn, self.bindpw)

        return self.__conn

    @property
    def naming_context(self) -> str:
        """
        Default naming context.

        :raises ValueError: If default naming context can not be obtained.
        :rtype: str
        """
        if not self.__naming_context:
            attr = 'defaultNamingContext'
            result = self.conn.search_s('', ldap.SCOPE_BASE, attrlist=[attr])
            if len(result) != 1:
                raise ValueError(f'Unexpected number of results for rootDSE query: {len(result)}')

            (_, values) = result[0]
            if attr not in values:
                raise ValueError(f'Unable to find {attr}')

            self.__naming_context = str(values[attr][0].decode('utf-8'))

        return self.__naming_context

    def ldap_result_to_dict(self, result: tuple[str, dict[str, list[bytes]]]) -> dict[str, dict[str, list[bytes]]]:
        """
        Convert result from python-ldap library from tuple into a dictionary
        to simplify lookup by distinguished name.

        :param result: Search result from python-ldap.
        :type result: tuple[str, dict[str, list[bytes]]]
        :return: Dictionary with distinguished name as key and attributes as value.
        :rtype: dict[str, dict[str, list[bytes]]]
        """
        return dict((dn, attrs) for dn, attrs in result if dn is not None)


class LDAPHost(ProviderHost):
    """
    LDAP host object.

    Provides features specific for native directory server like 389ds.
    """

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

        # Additional client configuration
        self.client.setdefault('id_provider', 'ldap')
        self.client.setdefault('ldap_uri', self.uri)

        # Backup of original data
        self.__backup: dict[str, dict[str, list[bytes]]] = None

    def backup(self) -> None:
        """
        Backup all directory server data.

        Full backup of ``cn=config`` and default naming context is performed.
        This is done by simple LDAP search on given base dn and remembering the
        contents. The operation is usually very fast.
        """
        if self.__backup is not None:
            return

        data = self.conn.search_s(self.naming_context, ldap.SCOPE_SUBTREE)
        config = self.conn.search_s('cn=config', ldap.SCOPE_BASE)

        dct = self.ldap_result_to_dict(data)
        dct.update(self.ldap_result_to_dict(config))
        self.__backup = dct

    def restore(self) -> None:
        """
        Restore directory server data.

        Current directory server content in ``cn=config`` and default naming
        context is modified to its original data. This is done by computing a
        difference between original data obtained by :func:`backup` and then
        calling add, delete and modify operations to convert current state to
        the original state. This operation is usually very fast.
        """
        data = self.conn.search_s(self.naming_context, ldap.SCOPE_SUBTREE)
        config = self.conn.search_s('cn=config', ldap.SCOPE_BASE)

        # Convert list of tuples to dictionary for better lookup
        data = self.ldap_result_to_dict(data)
        data.update(self.ldap_result_to_dict(config))

        for dn, attrs in reversed(data.items()):
            # Restore records that were modified
            if dn in self.__backup:
                original_attrs = self.__backup[dn]
                modlist = ldap.modlist.modifyModlist(attrs, original_attrs)
                if modlist:
                    self.conn.modify_s(dn, modlist)

        for dn, attrs in reversed(data.items()):
            # Delete records that were added
            if dn not in self.__backup:
                self.conn.delete_s(dn)
                continue

        for dn, attrs in self.__backup.items():
            # Add back records that were deleted
            if dn not in data:
                self.conn.add_s(dn, list(attrs.items()))


class IPAHost(ProviderHost):
    """
    IPA host object.

    Provides features specific for IPA server.
    """

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

        self.adminpw = self.config.get('adminpw', 'Secret123')

        # Additional client configuration
        self.client.setdefault('id_provider', 'ipa')
        self.client.setdefault('access_provider', 'ipa')
        self.client.setdefault('ipa_server', self.hostname)
        self.client.setdefault('ipa_domain', self.domain)
        self.client.setdefault('dyndns_update', False)

        # Backup of original data
        self.__backup: str = None

    def kinit(self) -> None:
        """
        Obtain ``admin`` user Kerberos TGT.
        """
        self.exec(['kinit', 'admin'], stdin=self.adminpw)

    def backup(self) -> None:
        """
        Backup all IPA server data.

        This is done by calling ``ipa-backup --data --online`` on the server
        and can take several seconds to finish.
        """
        if self.__backup is not None:
            return

        self.exec('ipa-backup --data --online')
        cmd = self.exec('ls /var/lib/ipa/backup | tail -n 1')
        self.__backup = cmd.stdout.strip()

    def restore(self) -> None:
        """
        Restore all IPA server data to its original state.

        This is done by calling ``ipa-restore --data --online`` on the server
        and can take several seconds to finish.
        """
        if self.__backup is None:
            return

        self.exec(['ipa-restore', '--unattended', '--password', self.bindpw, '--data', '--online', self.__backup])


class SambaHost(ProviderHost):
    """
    Samba host object.

    Provides features specific for Samba server.
    """

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

        # Additional client configuration
        self.client.setdefault('id_provider', 'ad')
        self.client.setdefault('access_provider', 'ad')
        self.client.setdefault('ad_server', self.hostname)
        self.client.setdefault('ad_domain', self.domain)
        self.client.setdefault('dyndns_update', False)

        # Backup of original data
        self.__backup: bool = None

    def backup(self) -> None:
        """
        Backup all Samba server data.

        This is done by creating a backup of Samba database. This operation
        is usually very fast.
        """
        if self.__backup is not None:
            return

        self.exec('''
            set -e
            systemctl stop samba
            rm -fr /var/lib/samba.bak
            cp -r /var/lib/samba /var/lib/samba.bak
            systemctl start samba
        ''')
        self.__backup = True

    def restore(self) -> None:
        """
        Restore all Samba server data to its original value.

        This is done by overriding current database with the backup created
        by :func:`backup`. This operation is usually very fast.
        """
        if self.__backup is None:
            return

        self.exec('''
            set -e
            systemctl stop samba
            rm -fr /var/lib/samba
            cp -r /var/lib/samba.bak /var/lib/samba
            systemctl start samba
        ''')


class ADHost(ProviderHost):
    """
    Active Directory host object.

    Provides features specific for Active Directory domain controller.

    .. warning::

        Backup and restore functionality of a domain controller is quite limited
        when compared to other services. Unfortunately, a full backup and
        restore of a domain controller is not possible without a complete system
        backup and reboot which takes too long time and is not suitable for
        setting an exact state for each test. Therefore a limited backup and
        restore is provided which only deletes all added objects. It works well
        if a test does not modify any existing data but only uses new
        objects like newly added users and groups.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs, tls=False)

        self.binddn = self.config.get('binddn', f'Administrator@{self.domain}')

        # Additional client configuration
        self.client.setdefault('id_provider', 'ad')
        self.client.setdefault('access_provider', 'ad')
        self.client.setdefault('ad_server', self.hostname)
        self.client.setdefault('ad_domain', self.domain)
        self.client.setdefault('dyndns_update', False)

        # Backup of original data
        self.__backup: bool = None

    def exec(
        self,
        argv: str | list[any] | tuple[any],
        *,
        cwd: str = None,
        stdin: str | bytes = None,
        env: dict[str, any] = dict(),
        log_stdout: bool = True,
        raise_on_error: bool = True,
        wait: bool = True
    ) -> RemoteCommandResult:
        """
        Execute command on remote host inside a powershell.

        :param argv: Command or script to execute as string or argv list.
        :type argv: str | list[any] | tuple[any]
        :param cwd: Working directory where the command should be executed, defaults to None
        :type cwd: str, optional
        :param stdin: Standard input, defaults to None
        :type stdin: str | bytes, optional
        :param env: Environment variables, defaults to dict()
        :type env: dict[str, any], optional
        :param log_stdout: If True, command output is printed to the logger, defaults to True
        :type log_stdout: bool, optional
        :param raise_on_error: Raise ``subprocess.CalledProcessError`` on non-zero return code, defaults to True
        :type raise_on_error: bool, optional
        :param wait: Wait for the command to finish, defaults to True
        :type wait: bool, optional
        :raises ValueError: If argv or cwd is empty.
        :raises TypeError: If argv is instance of unsupported type.
        :return: Command result, if ``wait`` is set to False, you need to call ``res.wait()``.
        :rtype: RemoteCommandResult
        """
        if not argv:
            raise ValueError('Parameter "argv" can not be empty.')

        if not isinstance(argv, (str, list, tuple)):
            raise TypeError('Parameter "argv" can be: str, list[any], tuple[any]')

        if cwd is not None and not cwd:
            raise ValueError('Parameter "cwd" can not be empty.')

        if stdin is not None:
            raise ValueError('stdin is not supported on Windows host')

        command = self._open_shell(
            'powershell -NonInteractive -Command -',
            argv, log_stdout=log_stdout, encoding='utf-8'
        )

        def write(str: str) -> None:
            command.stdin.write(str.encode('utf-8'))

        # Set environment
        for key, value in env.items():
            value = self.__escape_argv(value)
            write(f'$Env:{key} = "{value}"\n')

        # Set working directory
        if cwd is not None:
            arg = self.__escape_argv(cwd)
            write(f"cd '{arg}'\n")

        argv = [argv] if isinstance(argv, (str, bytes)) else [f"'{self.__escape_argv(x)}'" for x in argv]
        write(f"{' '.join(argv)}\n")
        write('exit\n')
        command.stdin.flush()
        command.raiseonerr = raise_on_error

        if wait:
            command.wait()

        return RemoteCommandResult(command)

    def backup(self) -> None:
        """
        Perform limited backup of the domain controller data. Currently only
        content under ``cn=users,$default_naming_context`` is backed up.

        This is done by performing simple LDAP search on the base dn. This
        operation is usually very fast.
        """
        if self.__backup is not None:
            return

        data = self.conn.search_s('cn=users,' + self.naming_context, ldap.SCOPE_SUBTREE)
        self.__backup = self.ldap_result_to_dict(data)

    def restore(self) -> None:
        """
        Perform limited restoration of the domain controller state.

        This is done by removing all records under
        ``cn=users,$default_naming_context`` that are not present in the
        original state.
        """
        # Currently, only users container is supported.
        data = self.conn.search_s('cn=users,' + self.naming_context, ldap.SCOPE_SUBTREE)

        # Convert list of tuples to dictionary for better lookup
        data = self.ldap_result_to_dict(data)

        # Modification of changed records or adding records that were deleted is
        # not supported due to constrains of various attributes that cannot be
        # written directly. Full AD backup restore is tedious and time consuming
        # operation that require machine reboot thus not something we can use.

        for dn in reversed(data.keys()):
            # Delete records that were added
            if dn not in self.__backup:
                self.conn.delete_s(dn)
                continue
