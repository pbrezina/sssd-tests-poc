from __future__ import annotations

from enum import Enum

import pytest

from ..multihost import Multihost
from ..topology import Topology


class TopologyMark(object):
    """
    Topology mark is used to describe test case requirements. It defines:

    * **name**, that is used to identify topology in pytest output
    * **topology** (:class:Topology) that is required to run the test
    * **fixtures** that are available during the test run
    * **domains** that will be automatically configured on the client

    .. code-block:: python
        :caption: Example usage

        @pytest.mark.topology(name, topology, domains, fixture1='path1', fixture2='path2', ...)
        def test_fixture_name(fixture1: BaseRole, fixture2: BaseRole, ...):
            assert True

    Fixture path points to a host in the multihost configuration and can be
    either in the form of ``$domain-type.$role`` (all host of given role) or
    ``$domain-type.$role[$index]`` (specific host on given index).

    The ``name`` is visible in verbose pytest output after the test name, for example:

    .. code-block:: console

        tests/test_basic.py::test_case (topology-name) PASSED
    """

    def __init__(
        self,
        name: str,
        topology: Topology,
        fixtures: dict[str, str] = dict(),
        domains: dict[str, str] = dict()
    ) -> None:
        """
        :param name: Topology name used in pytest output.
        :type name: str
        :param topology: Topology required to run the test.
        :type topology: Topology
        :param fixtures: Dynamically created fixtures available during the test run.
        :type fixtures: dict[str, str], optional
        :param domains: Automatically created SSSD domains on client host
        :type domains: dict[str, str], optional
        """

        self.name = name
        self.topology = topology
        self.fixtures = fixtures
        self.domains = domains

        self.mapping: dict[str, list[str]] = {}

        for fixture, target in self.fixtures.items():
            self.mapping.setdefault(target, list()).append(fixture)

    @property
    def args(self) -> set[str]:
        """
        Names of all dynamically created fixtures.
        """

        return list(self.fixtures.keys())

    def apply(self, mh: Multihost, funcargs: dict[str, any]) -> None:
        """
        Create required fixtures by modifying :attr:`pytest.Item.funcargs`.

        :param mh: _description_
        :type mh: Multihost
        :param funcargs: Pytest test item ``funcargs`` that will be modified.
        :type funcargs: dict[str, any]
        """

        for path, names in self.mapping.items():
            value = mh._lookup(path)
            for name in names:
                if name in funcargs:
                    funcargs[name] = value

    def export(self) -> dict:
        """
        Export the topology mark into a dictionary object that can be easily
        converted to JSON, YAML or other formats.

        .. code-block:: python

            {
                'name': 'client',
                'fixtures': { 'client': 'sssd.client[0]' },
                'domains': { 'test': 'sssd.ldap[0]' },
                'topology': [
                    {
                        'type': 'sssd',
                        'hosts': { 'client': 1 }
                    }
                ]
            }

        :rtype: dict
        """

        return {
            'name': self.name,
            'fixtures': self.fixtures,
            'domains': self.domains,
            'topology': self.topology.export(),
        }

    @classmethod
    def Create(cls, item: pytest.Item, mark: pytest.Mark) -> 'TopologyMark':
        """
        Create instance of :class:`TopologyMark` from ``@pytest.mark.topology``.

        :raises ValueError:
        :rtype: TopologyMark
        """

        error = f'{item.parent.nodeid}::{item.originalname}: invalid arguments for @pytest.mark.topology'

        if not mark.args or len(mark.args) > 3:
            raise ValueError(error)

        # Constructor for lib.multihost.KnownTopology
        if isinstance(mark.args[0], Enum):
            if len(mark.args) != 1:
                raise ValueError(error)

            if not isinstance(mark.args[0].value, cls):
                raise ValueError(error)

            return mark.args[0].value

        # Generic constructor.
        # First three parameters are positional, the rest are keyword arguments.
        if len(mark.args) != 2 and len(mark.args) != 3:
            raise ValueError(error)

        name = mark.args[0]
        topology = mark.args[1]
        domains = mark.args[2] if len(mark.args) == 3 else {}
        fixtures = mark.kwargs

        return cls(name, topology, fixtures, domains)
