from typing import Any, Union

from ..multihost import Multihost
from ..topology import Topology


class TopologyMark(object):
    def __init__(self, topology: Topology, fixtures: dict[str, str]) -> None:
        self.topology = topology
        self.fixtures = fixtures

    @property
    def args(self) -> set[str]:
        return set(self.topology.paths + list(self.fixtures.values()))

    def apply(self, mh: Multihost, funcargs: dict[str, Any]) -> None:
        for arg in self.topology.paths:
            value = mh.lookup(arg)

            if arg in funcargs:
                funcargs[arg] = value

            mapped = self.fixtures.get(arg, None)
            if mapped and mapped in funcargs:
                funcargs[mapped] = value
