from collections import Counter


class TopologyDomain(object):
    def __init__(self, type: str, **kwargs: dict[str, int]) -> None:
        self.type = type
        self.roles = kwargs

    def get(self, role: str) -> int:
        return self.roles[role]

    def describe(self) -> dict:
        return {'type': self.type, 'hosts': self.roles}

    def __str__(self) -> str:
        return str(self.describe())

    def __contains__(self, item: str) -> bool:
        return item in self.roles

    def __eq__(self, other) -> bool:
        return self.describe() == other.describe()

    def __ne__(self, other) -> bool:
        return self.describe() != other.describe()

    def __le__(self, other) -> bool:
        if self.type != other.type:
            return False

        for role, value in self.roles.items():
            if role not in other or other.get(role) < value:
                return False

        return True


class Topology(object):
    def __init__(self, *domains: tuple[TopologyDomain]) -> None:
        self.domains = list(domains)
        self._paths = None

    @property
    def paths(self) -> list[str]:
        if self._paths is not None:
            return self._paths

        paths = []
        for domain in self.domains:
            for role, count in domain.roles.items():
                paths.append(f'{domain.type}_{role}_list')
                for i in range(0, count):
                    paths.append(f'{domain.type}_{role}_{i}')

        self._paths = paths
        return self._paths

    def get(self, type: str) -> TopologyDomain:
        for domain in self.domains:
            if domain.type == type:
                return domain

        raise KeyError(f'Domain "{type}" was not found.')

    def describe(self) -> dict:
        out = []
        for domain in self.domains:
            out.append(domain.describe())

        return out

    def __str__(self) -> str:
        return str(self.describe())

    def __contains__(self, item: str) -> bool:
        try:
            return self.get(item) is not None
        except KeyError:
            return False

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, self.__class__):
            return NotImplemented

        return self.describe() == other.describe()

    def __ne__(self, other: object) -> bool:
        return not self == other

    def __le__(self, other: object) -> bool:
        if not isinstance(other, self.__class__):
            return NotImplemented

        for domain in self.domains:
            if domain.type not in other:
                return False

            if not domain <= other.get(domain.type):
                return False

        return True

    @classmethod
    def FromMultihostConfig(cls, mhc):
        if mhc is None:
            return cls()

        topology = []
        for domain in mhc.get('domains', []):
            topology.append({
                'type': domain['type'],
                'hosts': dict(Counter([x['role'] for x in domain['hosts']]))
            })

        domains = [TopologyDomain(x.get('type', 'default'), **x['hosts']) for x in topology]
        return cls(*domains)

    # WellKnown Topology List
    JustClient = [
        TopologyDomain('sssd', client=1),
        {'sssd_client_0': 'client'},
    ]
    LDAP = [
        TopologyDomain('sssd', client=1, ldap=1),
        {'sssd_client_0': 'client', 'sssd_ldap_0': 'ldap'},
    ]
    IPA = [
        TopologyDomain('sssd', client=1, ipa=1),
        {'sssd_client_0': 'client', 'sssd_ipa_0': 'ipa'},
    ]
    AD = [
        TopologyDomain('sssd', client=1, ad=1),
        {'sssd_client_0': 'client', 'sssd_ad_0': 'ad'},
    ]
