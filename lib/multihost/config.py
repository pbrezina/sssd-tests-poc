import pytest_multihost
import copy

from .topology import Topology, TopologyDomain, TopologyRole


class MultihostHost(pytest_multihost.host.BaseHost):
    attrs: dict[str, any]

    @classmethod
    def from_dict(cls, dct: dict[str, any], domain: 'MultihostDomain') -> 'MultihostHost':
        attrs = dct.pop('attrs', dict())
        obj = super().from_dict(dct, domain)
        obj.attrs = attrs

        return obj


class MultihostDomain(pytest_multihost.config.Domain):
    attrs: dict[str, any]

    @property
    def host_classes(self):
        return {
            'default': MultihostHost,
        }

    @classmethod
    def from_dict(cls, dct: dict[str, any], config: 'MultihostConfig') -> 'MultihostDomain':
        attrs = dct.pop('attrs', dict())
        obj = super().from_dict(dct, config)
        obj.attrs = attrs

        return obj


class MultihostConfig(pytest_multihost.config.Config):
    def __init__(self, **kwargs) -> None:
        self.attrs = kwargs
        super().__init__(**kwargs)

    def get_domain_class(self):
        return MultihostDomain

    def filter(self, description):
        pass

    def fulfils(self, topology, exact=False):
        return True

    def scope(self, topology: Topology) -> 'MultihostConfig':
        scoped = copy.deepcopy(self)

        new_domains = []
        remainder = self.domains
        for topology_domain in topology.domains:
            keep = []
            for mh_domain in remainder:
                if self._filter_domain(mh_domain, topology_domain):
                    new_domains.append(mh_domain)
                else:
                    keep.append(mh_domain)
            remainder = keep

        scoped.domains = new_domains

        return scoped

    def _filter_domain(self, mh_domain: MultihostDomain, topology_domain: TopologyDomain) -> bool:
        if mh_domain.type != topology_domain.type:
            return False

        # todo match attrs

        new_hosts = []
        remainder = mh_domain =
        for topology_domain in topology.domains:
            keep = []
            for mh_domain in remainder:
                if self._filter_domain(mh_domain, topology_domain):
                    new_hosts.append(mh_domain)
                else:
                    keep.append(mh_domain)
            remainder = keep

        scoped.domains = new_hosts

        return True
