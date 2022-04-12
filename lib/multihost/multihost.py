from types import SimpleNamespace
from typing import Union

from pytest_multihost.config import Domain
from pytest_multihost.plugin import MultihostFixture

from .roles import BaseRole


class Multihost(object):
    def __init__(self, multihost_fixture: MultihostFixture) -> None:
        self.fixture = multihost_fixture
        self._hosts = {}
        self._groups = {}

        for domain in self.fixture.config.domains:
            setattr(self, domain.type, self._domain_to_namespace(domain))

    def _domain_to_namespace(self, domain: Domain) -> SimpleNamespace:
        ns = SimpleNamespace()
        for role in domain.roles:
            hosts = [BaseRole(role, host) for host in domain.hosts_by_role(role)]

            self._groups[f'{domain.type}_{role}_list'] = hosts
            for index, host in enumerate(hosts):
                self._hosts[f'{domain.type}_{role}_{index}'] = host

            setattr(ns, role, hosts)

        return ns

    def lookup(self, path: str) -> Union[BaseRole, list[BaseRole]]:
        table = self._groups if path.endswith('_list') else self._hosts
        if path not in table:
            raise LookupError(f'Host "{path}" does not exist')

        return table[path]

    def teardown(self) -> None:
        for host in reversed(self._hosts.values()):
            host.teardown()

    def __enter__(self) -> 'Multihost':
        return self

    def __exit__(self, exception_type, exception_value, traceback) -> None:
        self.teardown()
