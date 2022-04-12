from typing import Any, Union

from .. import Multihost, Topology, TopologyDomain


class TopologyMarker(object):
    def __init__(self, *args: Union[TopologyDomain, dict[str, str]]) -> None:
        (domains, mapping) = self._process_args(args)

        self.topology = Topology(*domains)
        self.mapping = mapping

    @property
    def args(self) -> set[str]:
        return set(self.topology.paths + list(self.mapping.values()))

    def apply(self, mh: Multihost, funcargs: dict[str, Any]) -> None:
        for arg in self.topology.paths:
            value = mh.lookup(arg)

            if arg in funcargs:
                funcargs[arg] = value

            mapped = self.mapping.get(arg, None)
            if mapped and mapped in funcargs:
                funcargs[mapped] = value

    def _process_args(self, args) -> tuple[list[TopologyDomain], dict[str, str]]:
        args = self._expand_args(args)

        for arg in args:
            if not isinstance(arg, (TopologyDomain, dict)):
                raise ValueError(f'{arg} is not instance of TopologyDomain or dict')

        domains = [x for x in args if isinstance(x, TopologyDomain)]
        mapping = [x for x in args if isinstance(x, dict)]
        mapping = {k: v for d in mapping for k, v in d.items()}

        return (domains, mapping)

    def _expand_args(self, args) -> list[Union[TopologyDomain, dict[str, str]]]:
        # For convenience, arguments may have been added as a list. Expand it.
        expanded = []
        for x in args:
            if isinstance(x, list):
                expanded.extend(x)
            else:
                expanded.append(x)

        return expanded
