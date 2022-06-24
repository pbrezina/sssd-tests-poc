from __future__ import annotations

import textwrap

from ..command import RemoteCommandResult
from .base import BaseObject, WindowsRole


class AD(WindowsRole):
    """
    AD service management.
    """

    def setup(self) -> None:
        """
        Setup AD role.

        #. backup AD data
        """
        super().setup()
        self.host.backup()

    def teardown(self) -> None:
        """
        Teardown AD role.

        #. restore original AD data
        """
        self.host.restore()
        super().teardown()

    def user(self, name: str) -> ADUser:
        """
        Get user object.

        :param name: User name.
        :type name: str
        :return: New user object.
        :rtype: ADUser
        """
        return ADUser(self, name)

    def group(self, name: str) -> ADGroup:
        """
        Get group object.

        :param name: Group name.
        :type name: str
        :return: New group object.
        :rtype: ADGroup
        """
        return ADGroup(self, name)


class ADObject(BaseObject):
    """
    Base AD object class.
    """

    def __init__(self, role: AD, command_group: str, name: str) -> None:
        """
        :param role: AD role object.
        :type role: AD
        :param command_group: AD command group.
        :type command_group: str
        :param name: Object name.
        :type name: str
        """
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
        """
        Delete object from AD.
        """
        self._exec('Remove', self._build_args(self._identity))

    def get(self, attrs: list[str] | None = None) -> dict[str, list[str]]:
        """
        Get AD object attributes.

        :param attrs: If set, only requested attributes are returned, defaults to None
        :type attrs: list[str] | None, optional
        :return: Dictionary with attribute name as a key.
        :rtype: dict[str, list[str]]
        """
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

    def _build_args(self, attrs: dict[str, tuple[BaseObject.cli, any]], as_script: bool = True):
        return super()._build_args(attrs, as_script=as_script)


class ADUser(ADObject):
    """
    AD user management.
    """

    def __init__(self, role: AD, name: str) -> None:
        """
        :param role: AD role object.
        :type role: AD
        :param name: User name.
        :type name: str
        """
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
        """
        Create new AD user.

        Parameters that are not set are ignored.

        :param uid: User id, defaults to None
        :type uid: int | None, optional
        :param gid: Primary group id, defaults to None
        :type gid: int | None, optional
        :param password: Password (cannot be None), defaults to 'Secret123'
        :type password: str, optional
        :param home: Home directory, defaults to None
        :type home: str | None, optional
        :param gecos: GECOS, defaults to None
        :type gecos: str | None, optional
        :param shell: Login shell, defaults to None
        :type shell: str | None, optional
        :return: Self.
        :rtype: ADUser
        """
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
        """
        Modify existing AD user.

        Parameters that are not set are ignored. If needed, you can delete an
        attribute by setting the value to ``AD.Flags.DELETE``.

        :param uid: User id, defaults to None
        :type uid: int | AD.Flags | None, optional
        :param gid: Primary group id, defaults to None
        :type gid: int | AD.Flags | None, optional
        :param home: Home directory, defaults to None
        :type home: str | AD.Flags | None, optional
        :param gecos: GECOS, defaults to None
        :type gecos: str | AD.Flags | None, optional
        :param shell: Login shell, defaults to None
        :type shell: str | AD.Flags | None, optional
        :return: Self.
        :rtype: ADUser
        """
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
    """
    AD group management.
    """

    def __init__(self, role: AD, name: str) -> None:
        """
        :param role: AD role object.
        :type role: AD
        :param name: Group name.
        :type name: str
        """
        super().__init__(role, 'group', name)

    def add(
        self,
        *,
        gid: int | None = None,
        description: str | None = None,
        scope: str = 'Global',
        category: str = 'Security',
    ) -> ADGroup:
        """
        Create new AD group.

        :param gid: Group id, defaults to None
        :type gid: int | None, optional
        :param description: Description, defaults to None
        :type description: str | None, optional
        :param scope: Scope ('Global', 'Universal', 'DomainLocal'), defaults to 'Global'
        :type scope: str, optional
        :param category: Category ('Distribution', 'Security'), defaults to 'Security'
        :type category: str, optional
        :return: Self.
        :rtype: ADGroup
        """
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
        """
        Modify existing AD group.

        Parameters that are not set are ignored. If needed, you can delete an
        attribute by setting the value to ``AD.Flags.DELETE``.

        :param gid: Group id, defaults to None
        :type gid: int | AD.Flags | None, optional
        :param description: Description, defaults to None
        :type description: str | AD.Flags | None, optional
        :return: Self.
        :rtype: ADUser
        """
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
        """
        Add group member.

        :param member: User or group to add as a member.
        :type member: ADUser | ADGroup
        :return: Self.
        :rtype: ADGroup
        """
        return self.add_members([member])

    def add_members(self, members: list[ADUser | ADGroup]) -> ADGroup:
        """
        Add multiple group members.

        :param member: List of users or groups to add as members.
        :type member: list[ADUser | ADGroup]
        :return: Self.
        :rtype: ADGroup
        """
        return self.role.host.exec(textwrap.dedent(f'''
            Import-Module ActiveDirectory
            Add-ADGroupMember -Identity '{self.name}' -Members '{self.__get_members(members)}'
        ''').strip())
        return self

    def remove_member(self, member: ADUser | ADGroup) -> ADGroup:
        """
        Remove group member.

        :param member: User or group to remove from the group.
        :type member: ADUser | ADGroup
        :return: Self.
        :rtype: ADGroup
        """
        return self.remove_members([member])

    def remove_members(self, members: list[ADUser | ADGroup]) -> ADGroup:
        """
        Remove multiple group members.

        :param member: List of users or groups to remove from the group.
        :type member: list[ADUser | ADGroup]
        :return: Self.
        :rtype: ADGroup
        """
        return self.role.host.exec(textwrap.dedent(f'''
            Import-Module ActiveDirectory
            Remove-ADGroupMember -Identity '{self.name}' -Members '{self.__get_members(members)}'
        ''').strip())
        return self

    def __get_members(self, members: list[ADUser | ADGroup]) -> str:
        return ','.join([x.name for x in members])
