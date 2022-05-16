from __future__ import annotations

import ldap.modlist

from .base import BaseObject, LinuxRole


class Samba(LinuxRole):
    def setup(self) -> None:
        super().setup()
        self.host.backup()

    def teardown(self) -> None:
        self.host.restore()
        super().teardown()

    def user(self, name: str) -> SambaUser:
        return SambaUser(self, name)

    def group(self, name: str) -> SambaGroup:
        return SambaGroup(self, name)


class SambaObject(BaseObject):
    def __init__(self, role: Samba, command: str, name: str) -> None:
        super().__init__()
        self.role = role
        self.command = command
        self.name = name

    def _exec(self, op: str, args: list[str] = list(), **kwargs) -> None:
        return self.role.host.exec(['samba-tool', self.command, op, self.name, *args], **kwargs)

    def _add(self, attrs: dict[str, tuple[BaseObject.cli, any]]) -> None:
        self._exec('add', self._build_args(attrs))

    def _modify(self, attrs: dict[str, any | list[any] | Samba.Flags | None]) -> None:
        obj = self.get()

        # Remove dn and distinguishedName attributes
        dn = obj.pop('dn')[0]
        del obj['distinguishedName']

        # Build old attrs
        old_attrs = {k: [str(i).encode('utf-8') for i in v] for k, v in obj.items()}

        # Update object
        for attr, value in attrs.items():
            if value is None:
                continue

            if value == Samba.Flags.DELETE:
                del obj[attr]
                continue

            if not isinstance(value, list):
                obj[attr] = [str(value)]
                continue

            obj[attr] = [str(x) for x in value]

        # Build new attrs
        new_attrs = {k: [str(i).encode('utf-8') for i in v] for k, v in obj.items()}

        # Build diff
        modlist = ldap.modlist.modifyModlist(old_attrs, new_attrs)
        if modlist:
            self.role.host.conn.modify_s(dn, modlist)

    def delete(self) -> None:
        self._exec('delete')

    def get(self, attrs: list[str] | None = None) -> dict[str, list[str]]:
        cmd = self._exec('show')
        return self._parse_attrs(cmd.stdout_lines, attrs)


class SambaUser(SambaObject):
    def __init__(self, role: Samba, name: str) -> None:
        super().__init__(role, 'user', name)

    def add(
        self,
        *,
        uid: int | None = None,
        gid: int | None = None,
        password: str | None = 'Secret123',
        home: str | None = None,
        gecos: str | None = None,
        shell: str | None = None,
        extra: dict[str, any] = dict()
    ) -> SambaUser:
        attrs = {
            'password': (self.cli.POSITIONAL, password),
            'given-name': (self.cli.VALUE, self.name),
            'surname': (self.cli.VALUE, self.name),
            'uid-number': (self.cli.VALUE, uid),
            'gid-number': (self.cli.VALUE, gid),
            'unix-home': (self.cli.VALUE, home),
            'gecos': (self.cli.VALUE, gecos),
            'login-shell': (self.cli.VALUE, shell),
            **extra,
        }

        self._add(attrs)
        return self

    def modify(
        self,
        *,
        uid: int | Samba.Flags | None = None,
        gid: int | Samba.Flags | None = None,
        home: str | Samba.Flags | None = None,
        gecos: str | Samba.Flags | None = None,
        shell: str | Samba.Flags | None = None,
        extra: dict[str, any | list[any] | Samba.Flags | None] = dict()
    ) -> SambaUser:
        attrs = {
            'uidNumber': uid,
            'gidNumber': gid,
            'unixHomeDirectory': home,
            'gecos': gecos,
            'loginShell': shell,
            **extra,
        }

        self._modify(attrs)
        return self


class SambaGroup(SambaObject):
    def __init__(self, role: Samba, name: str) -> None:
        super().__init__(role, 'group', name)

    def add(
        self,
        *,
        gid: int | None = None,
        description: str | None = None,
        scope: str = 'Global',
        category: str = 'Security',
        extra: dict[str, any] = dict()
    ) -> SambaGroup:
        attrs = {
            'gid-number': (self.cli.VALUE, gid),
            'description': (self.cli.VALUE, description),
            'group-scope': (self.cli.VALUE, scope),
            'group-type': (self.cli.VALUE, category),
            **extra,
        }

        self._add(attrs)
        return self

    def modify(
        self,
        *,
        gid: int | Samba.Flags | None = None,
        description: str | Samba.Flags | None = None,
        extra: dict[str, any | list[any] | Samba.Flags | None] = dict()
    ) -> SambaUser:
        attrs = {
            'gidNumber': gid,
            'description': description,
            **extra,
        }

        self._modify(attrs)
        return self

    def add_member(self, member: SambaUser | SambaGroup) -> SambaGroup:
        return self.add_members([member])

    def add_members(self, members: list[SambaUser | SambaGroup]) -> SambaGroup:
        self._exec('addmembers', self.__get_member_args(members))
        return self

    def remove_member(self, member: SambaUser | SambaGroup) -> SambaGroup:
        return self.remove_members([member])

    def remove_members(self, members: list[SambaUser | SambaGroup]) -> SambaGroup:
        self._exec('removemembers', self.__get_member_args(members))
        return self

    def __get_member_args(self, members: list[SambaUser | SambaGroup]) -> list[str]:
        return [','.join([x.name for x in members])]
