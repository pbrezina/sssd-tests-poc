from __future__ import annotations

from types import SimpleNamespace
from typing import TYPE_CHECKING

import pytest
from pytest_multihost.config import Domain

from .config import MultihostConfig
from .host import BaseHost
from .roles import BaseRole, get_role_class
from .topology import Topology, TopologyDomain

if TYPE_CHECKING:
    from .plugin.plugin import MultihostItemData


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

    def __init__(self, request: pytest.FixtureRequest, multihost: MultihostConfig, topology: Topology) -> None:
        """
        :param multihost: Multihost configuration.
        :type multihost: MultihostConfig
        """

        self.data: MultihostItemData = request.node.multihost
        self.request = request
        self.multihost = multihost
        self._paths = {}

        for domain in self.multihost.domains:
            if domain.type in topology:
                setattr(self, domain.type, self._domain_to_namespace(domain, topology.get(domain.type)))

    def _domain_to_namespace(self, domain: Domain, topology_domain: TopologyDomain) -> SimpleNamespace:
        ns = SimpleNamespace()
        for role in domain.roles:
            if role not in topology_domain:
                continue

            count = topology_domain.get(role)
            hosts = [self._host_to_role(host) for host in domain.hosts_by_role(role)[:count]]

            self._paths[f'{domain.type}.{role}'] = hosts
            for index, host in enumerate(hosts):
                self._paths[f'{domain.type}.{role}[{index}]'] = host

            setattr(ns, role, hosts)

        return ns

    def _host_to_role(self, host: BaseHost):
        cls = get_role_class(host.role)
        return cls(self, host.role, host)

    def _lookup(self, path: str) -> BaseRole | list[BaseRole]:
        """
        Lookup host by path. The path format is ``$domain.$role``
        or ``$domain.$role[$index]``

        :param path: Host path.
        :type path: str
        :raises LookupError: If host is not found.
        :return: The role object if index was given, list of role objects otherwise.
        :rtype: BaseRole | list[BaseRole]
        """

        if path not in self._paths:
            raise LookupError(f'Name "{path}" does not exist')

        return self._paths[path]

    def _setup(self) -> None:
        """
        Setup multihost. A setup method is called on each host to initialize the
        host to expected state.
        """
        for role in self._paths.values():
            if isinstance(role, BaseRole):
                role.setup()

    def _teardown(self) -> None:
        """
        Teardown multihost. The purpose of this method is to revert any changes
        that were made during a test run. It is automatically called when the
        test is finished.
        """
        errors = []
        for role in reversed(self._paths.values()):
            if isinstance(role, BaseRole):
                try:
                    role.collect_artifacts()
                    role.teardown()
                except Exception as e:
                    errors.append(e)

        if errors:
            raise Exception(errors)

    def __enter__(self) -> 'Multihost':
        self._setup()
        return self

    def __exit__(self, exception_type, exception_value, traceback) -> None:
        self._teardown()
