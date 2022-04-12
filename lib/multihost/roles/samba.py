from __future__ import annotations

import ldap.modlist

from .base import BaseObject, LinuxRole


class Samba(LinuxRole):
    """
    Samba service management.
    """

    def setup(self) -> None:
        """
        Setup Samba role.

        #. backup Samba data
        """
        super().setup()
        self.host.backup()

    def teardown(self) -> None:
        """
        Teardown Samba role.

        #. restore original Samba data
        """
        self.host.restore()
        super().teardown()

    def user(self, name: str) -> SambaUser:
        """
        Get user object.

        :param name: User name.
        :type name: str
        :return: New user object.
        :rtype: SambaUser
        """
        return SambaUser(self, name)

    def group(self, name: str) -> SambaGroup:
        """
        Get group object.

        :param name: Group name.
        :type name: str
        :return: New group object.
        :rtype: SambaGroup
        """
        return SambaGroup(self, name)


class SambaObject(BaseObject):
    """
    Base Samba object class.
    """

    def __init__(self, role: Samba, command: str, name: str) -> None:
        """
        :param role: Samba role object.
        :type role: Samba
        :param command: Samba command group.
        :type command: str
        :param name: Object name.
        :type name: str
        """
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
        """
        Delete object from Samba.
        """
        self._exec('delete')

    def get(self, attrs: list[str] | None = None) -> dict[str, list[str]]:
        """
        Get Samba object attributes.

        :param attrs: If set, only requested attributes are returned, defaults to None
        :type attrs: list[str] | None, optional
        :return: Dictionary with attribute name as a key.
        :rtype: dict[str, list[str]]
        """
        cmd = self._exec('show')
        return self._parse_attrs(cmd.stdout_lines, attrs)


class SambaUser(SambaObject):
    """
    Samba user management.
    """

    def __init__(self, role: Samba, name: str) -> None:
        """
        :param role: Samba role object.
        :type role: Samba
        :param name: User name.
        :type name: str
        """
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
    ) -> SambaUser:
        """
        Create new Samba user.

        Parameters that are not set are ignored.

        :param uid: User id, defaults to None
        :type uid: int | None, optional
        :param gid: Primary group id, defaults to None
        :type gid: int | None, optional
        :param password: Password, defaults to 'Secret123'
        :type password: str, optional
        :param home: Home directory, defaults to None
        :type home: str | None, optional
        :param gecos: GECOS, defaults to None
        :type gecos: str | None, optional
        :param shell: Login shell, defaults to None
        :type shell: str | None, optional
        :return: Self.
        :rtype: SambaUser
        """
        attrs = {
            'password': (self.cli.POSITIONAL, password),
            'given-name': (self.cli.VALUE, self.name),
            'surname': (self.cli.VALUE, self.name),
            'uid-number': (self.cli.VALUE, uid),
            'gid-number': (self.cli.VALUE, gid),
            'unix-home': (self.cli.VALUE, home),
            'gecos': (self.cli.VALUE, gecos),
            'login-shell': (self.cli.VALUE, shell),
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
    ) -> SambaUser:
        """
        Modify existing Samba user.

        Parameters that are not set are ignored. If needed, you can delete an
        attribute by setting the value to ``Samba.Flags.DELETE``.

        :param uid: User id, defaults to None
        :type uid: int | Samba.Flags | None, optional
        :param gid: Primary group id, defaults to None
        :type gid: int | Samba.Flags | None, optional
        :param home: Home directory, defaults to None
        :type home: str | Samba.Flags | None, optional
        :param gecos: GECOS, defaults to None
        :type gecos: str | Samba.Flags | None, optional
        :param shell: Login shell, defaults to None
        :type shell: str | Samba.Flags | None, optional
        :return: Self.
        :rtype: SambaUser
        """
        attrs = {
            'uidNumber': uid,
            'gidNumber': gid,
            'unixHomeDirectory': home,
            'gecos': gecos,
            'loginShell': shell,
        }

        self._modify(attrs)
        return self


class SambaGroup(SambaObject):
    """
    Samba group management.
    """

    def __init__(self, role: Samba, name: str) -> None:
        """
        :param role: Samba role object.
        :type role: Samba
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
    ) -> SambaGroup:
        """
        Create new Samba group.

        :param gid: Group id, defaults to None
        :type gid: int | None, optional
        :param description: Description, defaults to None
        :type description: str | None, optional
        :param scope: Scope ('Global', 'Universal', 'DomainLocal'), defaults to 'Global'
        :type scope: str, optional
        :param category: Category ('Distribution', 'Security'), defaults to 'Security'
        :type category: str, optional
        :return: Self.
        :rtype: SambaGroup
        """
        attrs = {
            'gid-number': (self.cli.VALUE, gid),
            'description': (self.cli.VALUE, description),
            'group-scope': (self.cli.VALUE, scope),
            'group-type': (self.cli.VALUE, category),
        }

        self._add(attrs)
        return self

    def modify(
        self,
        *,
        gid: int | Samba.Flags | None = None,
        description: str | Samba.Flags | None = None,
    ) -> SambaUser:
        """
        Modify existing Samba group.

        Parameters that are not set are ignored. If needed, you can delete an
        attribute by setting the value to ``Samba.Flags.DELETE``.

        :param gid: Group id, defaults to None
        :type gid: int | Samba.Flags | None, optional
        :param description: Description, defaults to None
        :type description: str | Samba.Flags | None, optional
        :return: Self.
        :rtype: SambaUser
        """
        attrs = {
            'gidNumber': gid,
            'description': description,
        }

        self._modify(attrs)
        return self

    def add_member(self, member: SambaUser | SambaGroup) -> SambaGroup:
        """
        Add group member.

        :param member: User or group to add as a member.
        :type member: SambaUser | SambaGroup
        :return: Self.
        :rtype: SambaGroup
        """
        return self.add_members([member])

    def add_members(self, members: list[SambaUser | SambaGroup]) -> SambaGroup:
        """
        Add multiple group members.

        :param member: List of users or groups to add as members.
        :type member: list[SambaUser | SambaGroup]
        :return: Self.
        :rtype: SambaGroup
        """
        self._exec('addmembers', self.__get_member_args(members))
        return self

    def remove_member(self, member: SambaUser | SambaGroup) -> SambaGroup:
        """
        Remove group member.

        :param member: User or group to remove from the group.
        :type member: SambaUser | SambaGroup
        :return: Self.
        :rtype: SambaGroup
        """
        return self.remove_members([member])

    def remove_members(self, members: list[SambaUser | SambaGroup]) -> SambaGroup:
        """
        Remove multiple group members.

        :param member: List of users or groups to remove from the group.
        :type member: list[SambaUser | SambaGroup]
        :return: Self.
        :rtype: SambaGroup
        """
        self._exec('removemembers', self.__get_member_args(members))
        return self

    def __get_member_args(self, members: list[SambaUser | SambaGroup]) -> list[str]:
        return [','.join([x.name for x in members])]
