from types import SimpleNamespace
from typing import Union

from pytest_multihost.config import Domain

from .config import MultihostConfig
from .roles import BaseRole


class Multihost(object):
    """
    Multihost object provides access to underlaying multihost configuration,
    individual domains and hosts. This object should be used only in tests
    as the :func:`lib.multihost.plugin.mh` pytest fixture.

    Domains are accessible as dynamically created properties of this object,
    hosts are accessible by roles as dynamically created properties of each
    domain. Each host object is instance of specific role class from
    :mod:`lib.multihost.roles`.

    .. code-block:: yaml
        :caption: Example multihost configuration

        domains:
        - name: ldap.test
          type: sssd
          hosts:
          - name: client
            external_hostname: client.ldap.test
            role: client

          - name: ldap
            external_hostname: master.ldap.test
            role: ldap

    The configuration above creates one domain of type ``sssd`` with two hosts.
    The following example shows how to access the hosts:

    .. code-block:: python
        :caption: Example of the Multihost object

        def test_example(mh: Multihost):
            mh.sssd            # -> namespace containing roles as properties
            mh.sssd.client     # -> list of hosts providing given role
            mh.sssd.client[0]  # -> host object, instance of specific role
    """

    def __init__(self, multihost: MultihostConfig) -> None:
        """
        :param multihost: Multihost configuration.
        :type multihost: MultihostConfig
        """

        self.multihost = multihost
        self._paths = {}

        for domain in self.multihost.domains:
            setattr(self, domain.type, self._domain_to_namespace(domain))

    def _domain_to_namespace(self, domain: Domain) -> SimpleNamespace:
        ns = SimpleNamespace()
        for role in domain.roles:
            hosts = [BaseRole(role, host) for host in domain.hosts_by_role(role)]

            self._paths[f'{domain.type}.{role}'] = hosts
            for index, host in enumerate(hosts):
                self._paths[f'{domain.type}.{role}[{index}]'] = host

            setattr(ns, role, hosts)

        return ns

    def _lookup(self, path: str) -> Union[BaseRole, list[BaseRole]]:
        """
        Lookup host by path. The path format is ``$domain.$role``
        or ``$domain.$role[$index]``

        :param path: Host path.
        :type path: str
        :raises LookupError: If host is not found.
        :return: The role object if index was given, list of role objects otherwise.
        :rtype: Union[BaseRole, list[BaseRole]]
        """

        if path not in self._paths:
            raise LookupError(f'Name "{path}" does not exist')

        return self._paths[path]

    def _teardown(self) -> None:
        """
        Teardown multihost. The purpose of this method is to revert any changes
        that were made during a test run. It is automatically called when the
        test is finished.
        """
        for host in reversed(self._paths.values()):
            if isinstance(host, BaseRole):
                host.teardown()

    def __enter__(self) -> 'Multihost':
        return self

    def __exit__(self, exception_type, exception_value, traceback) -> None:
        self._teardown()
