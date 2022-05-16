from __future__ import annotations

import textwrap
from enum import Enum, auto

from ..command import RemoteCommandResult
from .base import BaseObject, WindowsRole


class AD(WindowsRole):
    class Flags(Enum):
        DELETE = auto()

    def setup(self) -> None:
        super().setup()
        self.host.backup()

    def teardown(self) -> None:
        self.host.restore()
        super().teardown()

    def user(self, name: str) -> ADUser:
        return ADUser(self, name)

    def group(self, name: str) -> ADGroup:
        return ADGroup(self, name)


class ADObject(BaseObject):
    def __init__(self, role: AD, command_group: str, name: str) -> None:
        super().__init__(cli_prefix='-')

        self.role = role
        self.command_group = command_group
        self.name = name
        self._identity = {'Identity': (self.cli.VALUE, self.name)}

    def _exec(self, op: str, args: list[str] = list(), **kwargs) -> RemoteCommandResult:
        return self.role.host.exec(textwrap.dedent(f'''
            Import-Module ActiveDirectory
            {op}-AD{self.command_group} {' '.join(args)}
        ''').strip(), **kwargs)

    def _add(self, attrs: dict[str, tuple[BaseObject.cli, any]]) -> None:
        self._exec('New', self._build_args(attrs))

    def _modify(self, attrs: dict[str, tuple[BaseObject.cli, any]]) -> None:
        self._exec('Set', self._build_args(attrs))

    def delete(self) -> None:
        self._exec('Remove', self._build_args(self._identity))

    def get(self, attrs: list[str] | None = None) -> dict[str, list[str]]:
        cmd = self._exec('Get', self._build_args(self._identity))
        return self._parse_attrs(cmd.stdout_lines, attrs)

    def _attrs_to_hash(self, attrs: dict[str, any]) -> str | None:
        out = ''
        for key, value in attrs.items():
            if value is not None:
                out += f'{key}="{value}";'

        if not out:
            return None

        return '@{' + out.rstrip(';') + '}'

    def _build_args(self, attrs: dict[str, tuple[BaseObject.cli, any]], quote: bool = True):
        return super()._build_args(attrs, quote=quote)


class ADUser(ADObject):
    def __init__(self, role: AD, name: str) -> None:
        super().__init__(role, 'user', name)

    def add(
        self,
        *,
        uid: int | None = None,
        gid: int | None = None,
        password: str = 'Secret123',
        home: str | None = None,
        gecos: str | None = None,
        shell: str | None = None,
    ) -> ADUser:
        unix_attrs = {
            'uid': self.name,
            'uidNumber': uid,
            'gidNumber': gid,
            'unixHomeDirectory': home,
            'gecos': gecos,
            'loginShell': shell
        }

        attrs = {
            'Name': (self.cli.VALUE, self.name),
            'AccountPassword': (self.cli.PLAIN, f'(ConvertTo-SecureString "{password}" -AsPlainText -force)'),
            'OtherAttributes': (self.cli.PLAIN, self._attrs_to_hash(unix_attrs)),
            'Enabled': (self.cli.PLAIN, '$true')
        }

        self._add(attrs)
        return self

    def modify(
        self,
        *,
        uid: int | AD.Flags | None = None,
        gid: int | AD.Flags | None = None,
        home: str | AD.Flags | None = None,
        gecos: str | AD.Flags | None = None,
        shell: str | AD.Flags | None = None,
    ) -> ADUser:
        unix_attrs = {
            'uidNumber': uid,
            'gidNumber': gid,
            'unixHomeDirectory': home,
            'gecos': gecos,
            'loginShell': shell
        }

        clear = [key for key, value in unix_attrs.items() if value == AD.Flags.DELETE]
        replace = {key: value for key, value in unix_attrs.items() if value is not None and value != AD.Flags.DELETE}

        attrs = {
            **self._identity,
            'Replace': (self.cli.PLAIN, self._attrs_to_hash(replace)),
            'Clear': (self.cli.PLAIN, ','.join(clear) if clear else None),
        }

        self._modify(attrs)
        return self


class ADGroup(ADObject):
    def __init__(self, role: AD, name: str) -> None:
        super().__init__(role, 'group', name)

    def add(
        self,
        *,
        gid: int | None = None,
        description: str | None = None,
        scope: str = 'Global',
        category: str = 'Security',
    ) -> ADGroup:
        unix_attrs = {
            'gidNumber': gid,
            'description': description,
        }

        attrs = {
            'Name': (self.cli.VALUE, self.name),
            'GroupScope': (self.cli.VALUE, scope),
            'GroupCategory': (self.cli.VALUE, category),
            'OtherAttributes': (self.cli.PLAIN, self._attrs_to_hash(unix_attrs)),
        }

        self._add(attrs)
        return self

    def modify(
        self,
        *,
        gid: int | AD.Flags | None = None,
        description: str | AD.Flags | None = None,
    ) -> ADUser:
        unix_attrs = {
            'gidNumber': gid,
            'description': description,
        }

        clear = [key for key, value in unix_attrs.items() if value == AD.Flags.DELETE]
        replace = {key: value for key, value in unix_attrs.items() if value is not None and value != AD.Flags.DELETE}

        attrs = {
            **self._identity,
            'Replace': (self.cli.PLAIN, self._attrs_to_hash(replace)),
            'Clear': (self.cli.PLAIN, ','.join(clear) if clear else None),
        }

        self._modify(attrs)
        return self

    def add_member(self, member: ADUser | ADGroup) -> ADGroup:
        return self.add_members([member])

    def add_members(self, members: list[ADUser | ADGroup]) -> ADGroup:
        return self.role.host.exec(textwrap.dedent(f'''
            Import-Module ActiveDirectory
            Add-ADGroupMember -Identity '{self.name}' -Members '{self.__get_members(members)}'
        ''').strip())
        return self

    def remove_member(self, member: ADUser | ADGroup) -> ADGroup:
        return self.remove_members([member])

    def remove_members(self, members: list[ADUser | ADGroup]) -> ADGroup:
        return self.role.host.exec(textwrap.dedent(f'''
            Import-Module ActiveDirectory
            Remove-ADGroupMember -Identity '{self.name}' -Members '{self.__get_members(members)}'
        ''').strip())
        return self

    def __get_members(self, members: list[ADUser | ADGroup]) -> str:
        return ','.join([x.name for x in members])
