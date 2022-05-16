from __future__ import annotations

from .base import BaseObject, LinuxRole


class IPA(LinuxRole):
    def setup(self) -> None:
        super().setup()
        self.host.backup()
        self.host.kinit()

    def teardown(self) -> None:
        self.host.restore()
        super().teardown()

    def user(self, name: str) -> IPAUser:
        return IPAUser(self, name)

    def group(self, name: str) -> IPAGroup:
        return IPAGroup(self, name)


class IPAObject(BaseObject):
    def __init__(self, role: IPA, command: str, name: str) -> None:
        super().__init__()
        self.role = role
        self.command = command
        self.name = name

    def _exec(self, op: str, args: list[str] = list(), **kwargs) -> None:
        return self.role.host.exec(['ipa', f'{self.command}-{op}', self.name, *args], **kwargs)

    def _add(self, attrs: dict[str, tuple[BaseObject.cli, any]], stdin: str | None = None):
        self._exec('add', self._build_args(attrs), stdin=stdin)

    def _modify(self, attrs: dict[str, tuple[BaseObject.cli, any]], stdin: str | None = None):
        self._exec('mod', self._build_args(attrs), stdin=stdin)

    def delete(self) -> None:
        self._exec('del')

    def get(self, attrs: list[str] | None = None) -> dict[str, list[str]]:
        cmd = self._exec('show', ['--all', '--raw'])

        # Remove first line that contains the object name and not attribute
        return self._parse_attrs(cmd.stdout_lines[1:], attrs)


class IPAUser(IPAObject):
    def __init__(self, role: IPA, name: str) -> None:
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
    ) -> IPAUser:
        attrs = {
            'first': (self.cli.VALUE, self.name),
            'last': (self.cli.VALUE, self.name),
            'uid': (self.cli.VALUE, uid),
            'gidnumber': (self.cli.VALUE, gid),
            'homedir': (self.cli.VALUE, home),
            'gecos': (self.cli.VALUE, gecos),
            'shell': (self.cli.VALUE, shell),
            'password': (self.cli.SWITCH, True) if password is not None else None,
        }

        self._add(attrs, stdin=password)
        return self

    def modify(
        self,
        *,
        uid: int | None = None,
        gid: int | None = None,
        password: str | None = None,
        home: str | None = None,
        gecos: str | None = None,
        shell: str | None = None,
    ) -> IPAUser:
        attrs = {
            'uid': (self.cli.VALUE, uid),
            'gidnumber': (self.cli.VALUE, gid),
            'homedir': (self.cli.VALUE, home),
            'gecos': (self.cli.VALUE, gecos),
            'shell': (self.cli.VALUE, shell),
            'password': (self.cli.SWITCH, True) if password is not None else None,
        }

        self._modify(attrs, stdin=password)
        return self


class IPAGroup(IPAObject):
    def __init__(self, role: IPA, name: str) -> None:
        super().__init__(role, 'group', name)

    def add(
        self,
        *,
        gid: int | None = None,
        description: str | None = None,
        nonposix: bool = False,
        external: bool = False,
    ) -> IPAGroup:
        attrs = {
            'gid': (self.cli.VALUE, gid),
            'desc': (self.cli.VALUE, description),
            'nonposix': (self.cli.SWITCH, True) if nonposix else None,
            'external': (self.cli.SWITCH, True) if external else None,
        }

        self._add(attrs)
        return self

    def modify(
        self,
        *,
        gid: int | None = None,
        description: str | None = None,
    ) -> IPAGroup:
        attrs = {
            'gid': (self.cli.VALUE, gid),
            'desc': (self.cli.VALUE, description),
        }

        self._modify(attrs)
        return self

    def add_member(self, member: IPAUser | IPAGroup) -> IPAGroup:
        return self.add_members([member])

    def add_members(self, members: list[IPAUser | IPAGroup]) -> IPAGroup:
        self._exec('add-member', self.__get_member_args(members))
        return self

    def remove_member(self, member: IPAUser | IPAGroup) -> IPAGroup:
        return self.remove_members([member])

    def remove_members(self, members: list[IPAUser | IPAGroup]) -> IPAGroup:
        self._exec('remove-member', self.__get_member_args(members))
        return self

    def __get_member_args(self, members: list[IPAUser | IPAGroup]) -> list[str]:
        users = [x for item in members if isinstance(item, IPAUser) for x in ('--users', item.name)]
        groups = [x for item in members if isinstance(item, IPAGroup) for x in ('--groups', item.name)]
        return [*users, *groups]
