from enum import Enum

import yaml

class TopologyRole(object):
    def __init__(self,
                 role: str,
                 count: int,
                 *,
                 attrs: dict[str, any] = None,
                 uuid: str = None,
                ) -> None:
        if not role:
            raise ValueError('Parameter "role" must not be empty.')

        if count <= 0:
            raise ValueError('Parameter "count" must be greater then zero.')

        self.role = role
        self.count = count
        self.uuid = role if not uuid else uuid
        self.attrs = attrs

    def export(self) -> dict[str, any]:
        return {
            'role': self.role,
            'uuid': self.uuid,
            'count': self.count,
            'attrs': self.attrs
        }

    def __str__(self) -> str:
        return str(self.export())

    @classmethod
    def Create(cls, repr: dict[str, any]):
        if not repr:
            raise ValueError('Parameter "repr" can not be empty')

        if not repr.get('role', None):
            raise ValueError('Can not create role without a role name')

        if repr.get('count', 0) <= 0:
            raise ValueError('Can not create role without a count attribute')

        return cls(repr['role'], repr['count'], uuid=repr.get('uuid', None), attrs=repr.get('attrs', None))


class TopologyDomain(object):
    def __init__(self, type: str, roles: list[TopologyRole], *, uuid: str = None, attrs: dict[str, any] = None) -> None:
        self.type = type
        self.roles = roles
        self.uuid = type if not uuid else uuid
        self.attrs = attrs

    def export(self) -> dict[str, any]:
        return {
            'type': self.type,
            'uuid': self.uuid,
            'attrs': self.attrs,
            'roles': self.roles.export()
        }

    def __str__(self) -> str:
        return str(self.export())

    @classmethod
    def Create(cls, repr: dict[str, any]):
        if not repr or not repr.get('type', None):
            raise ValueError('Can not create domain without a type')

        roles = []
        for role in repr.get('role', []):
            roles.append(TopologyRole.Create(role))

        return cls(repr['type'], roles, uuid=repr.get('uuid', None), attrs=repr.get('attrs', None))


class Topology(object):
    def __init__(self, *domains: TopologyDomain) -> None:
        self.domains = list(domains)
        self._paths = None

    @property
    def paths(self) -> list[str]:
        if self._paths is not None:
            return self._paths

        paths = []
        for domain in self.domains:
            for role in domain.roles:
                paths.append(f'{domain.uuid}_{role.uuid}_list')
                for i in range(0, role.count):
                    paths.append(f'{domain.uuid}_{role.uuid}_{i}')

        self._paths = paths
        return self._paths

    def export(self) -> dict[str, any]:
        out = []
        for domain in self.domains:
            out.append(domain.export())

        return out

    def __str__(self) -> str:
        return str(self.export())

    @classmethod
    def Create(cls, repr: list[dict[str, any]]) -> 'Topology':
        if not repr:
            return cls()

        domains = []
        for domain in repr:
            domains.append(TopologyDomain.Create(domain))

        return cls(*domains)

    @classmethod
    def CreateFromYaml(cls, y: str) -> 'Topology':
        return cls.Create(yaml.safe_load(y))


class Topologies(Enum):
    Client = [
        Topology.CreateFromYaml('''
        - type: 'sssd'
          roles:
          - role: client
            count: 1
        '''),
        {'sssd_client_0': 'client'},
    ]
    LDAP = [
        Topology.CreateFromYaml('''
        - type: sssd
          roles:
          - role: client
            count: 1
            attrs:
            - provider: ldap
          - role: ldap
            count: 1
        '''),
        {'sssd_client_0': 'client', 'sssd_ldap_0': 'ldap'},
    ]
    IPA = [
        Topology.CreateFromYaml('''
        - type: sssd
          roles:
          - role: client
            count: 1
            attrs:
            - provider: ipa
          - role: ad
            count: 1
        '''),
        {'sssd_client_0': 'client', 'sssd_ipa_0': 'ipa'},
    ]
    AD = [
        Topology.CreateFromYaml('''
        - type: sssd
          roles:
          - role: client
            count: 1
            attrs:
            - provider: ad
          - role: ad
            count: 1
        '''),
        {'sssd_client_0': 'client', 'sssd_ad_0': 'ad'},
    ]
