from __future__ import annotations

import base64
import hashlib
from typing import TYPE_CHECKING

import ldap
import ldap.ldapobject

from ..host import LDAPHost
from .base import BaseObject, LinuxRole

if TYPE_CHECKING:
    from ..multihost import Multihost


class LDAP(LinuxRole):
    def __init__(self, mh: Multihost, role: str, host: LDAPHost) -> None:
        super().__init__(mh, role, host)
        self.auto_uid = 23000
        self.auto_gid = 33000

    @property
    def conn(self) -> ldap.ldapobject.LDAPObject:
        return self.host.conn

    @property
    def naming_context(self) -> str:
        return self.host.naming_context

    def setup(self) -> None:
        super().setup()
        self.host.backup()

    def teardown(self) -> None:
        self.host.restore()
        super().teardown()

    def dn(self, rdn: str, basedn: LDAPObject | str | None = None) -> str:
        if not basedn:
            return f'{rdn},{self.naming_context}'

        if isinstance(basedn, LDAPObject):
            return f'{rdn},{basedn.dn}'

        return f'{rdn},{basedn},{self.naming_context}'

    def hash_password(self, password: str) -> str:
        # Compute hash value and convert it to format consumed by LDAP
        digest = hashlib.sha256(password.encode('utf-8')).digest()
        b64 = base64.b64encode(digest)

        return '{SHA256}' + b64.decode('utf-8')

    def add(self, dn: str, attrs: dict[str, list[str]]) -> None:
        addlist = []
        for attr, values in attrs.items():
            values = self.__values_to_bytes(values)

            # Skip if the value is None
            if values is None:
                continue

            addlist.append((attr, values))

        self.conn.add_s(dn, addlist)

    def delete(self, dn: str) -> None:
        self.conn.delete_s(dn)

    def modify(
        self,
        dn: str,
        *,
        add: dict[str, any | list[any] | None] = dict(),
        replace: dict[str, any | list[any] | None] = dict(),
        delete: dict[str, any | list[any] | None] = dict()
    ) -> None:
        modlist = []

        for attr, values in add.items():
            modlist.append((ldap.MOD_ADD, attr, self.__values_to_bytes(values)))

        for attr, values in replace.items():
            modlist.append((ldap.MOD_REPLACE, attr, self.__values_to_bytes(values)))

        for attr, values in delete.items():
            modlist.append((ldap.MOD_DELETE, attr, self.__values_to_bytes(values)))

        self.conn.modify_s(dn, modlist)

    def __values_to_bytes(self, values: any | list[any]) -> list[bytes]:
        if values is None:
            return None

        if not isinstance(values, list):
            values = [values]

        return [str(v).encode('utf-8') for v in values]

    def _generate_uid(self) -> int:
        self.auto_uid += 1
        return self.auto_uid

    def _generate_gid(self) -> int:
        self.auto_gid += 1
        return self.auto_gid

    def ou(self, name: str, basedn: LDAPObject | str | None = None) -> LDAPOrganizationalUnit:
        return LDAPOrganizationalUnit(self, name, basedn)

    def user(self, name: str, basedn: LDAPObject | str | None = None) -> LDAPUser:
        return LDAPUser(self, name, basedn)

    def group(self, name: str, basedn: LDAPObject | str | None = None, *, rfc2307bis: bool = False) -> LDAPGroup:
        return LDAPGroup(self, name, basedn, rfc2307bis=rfc2307bis)


class LDAPObject(BaseObject):
    def __init__(self, role: LDAP, rdn: str, basedn: LDAPObject | str | None = None) -> None:
        super().__init__()
        self.rdn = rdn
        self.basedn = basedn
        self.dn = role.dn(self.rdn, basedn)
        self.role = role

    def _default(self, value: any, default: any) -> any:
        if value is None:
            return default

        return value

    def _hash_password(self, password: str | None | LDAP.Flags) -> str | None | LDAP.Flags:
        if password is None or isinstance(password, LDAP.Flags):
            # Return unchanged value to simplify attribute modification
            return password

        return self.role.hash_password(password)

    def _add(self, attrs: dict[str, list[str]]) -> None:
        self.role.add(self.dn, attrs)

    def _modify(
        self,
        *,
        add: dict[str, any | list[any] | None] = dict(),
        replace: dict[str, any | list[any] | None] = dict(),
        delete: dict[str, any | list[any] | None] = dict()
    ) -> None:
        self.role.modify(self.dn, add=add, replace=replace, delete=delete)

    def _set(self, attrs: dict[str, any]) -> None:
        replace = {}
        delete = {}
        for attr, value in attrs.items():
            if value is None:
                continue

            if value == LDAP.Flags.DELETE:
                delete[attr] = None
                continue

            replace[attr] = value

        self.role.modify(self.dn, replace=replace, delete=delete)

    def delete(self) -> None:
        self.role.delete(self.dn)

    def get(self, attrs: list[str] | None = None, opattrs: bool = False) -> dict[str, list[str]]:
        attrs = ['*'] if attrs is None else attrs
        if opattrs:
            attrs.append('+')

        result = self.role.conn.search_s(self.dn, ldap.SCOPE_BASE, attrlist=attrs)
        if not result:
            return None

        if len(result) != 1:
            raise ValueError(f'Multiple objects returned on base search for {self.dn}')

        (_, attrs) = result[0]

        return {k: [i.decode('utf-8') for i in v] for k, v in attrs.items()}


class LDAPOrganizationalUnit(LDAPObject):
    def __init__(self, role: LDAP, name: str, basedn: LDAPObject | str | None = None) -> None:
        super().__init__(role, f'ou={name}', basedn)
        self.name = name

    def add(self) -> LDAPOrganizationalUnit:
        attrs = {
            'objectClass': 'organizationalUnit',
            'ou': self.name
        }

        self._add(attrs)
        return self


class LDAPUser(LDAPObject):
    def __init__(self, role: LDAP, name: str, basedn: LDAPObject | str | None = None) -> None:
        super().__init__(role, f'cn={name}', basedn)
        self.name = name

    def add(
        self,
        *,
        uid: int | None = None,
        gid: int | None = None,
        password: str | None = 'Secret123',
        home: str | None = None,
        gecos: str | None = None,
        shell: str | None = None
    ) -> LDAPUser:
        # Assign uid and gid automatically if not present to have the same
        # interface as other services.
        if uid is None:
            uid = self.role._generate_uid()

        if gid is None:
            gid = uid

        attrs = {
            'objectClass': 'posixAccount',
            'cn': self.name,
            'uid': self.name,
            'uidNumber': uid,
            'gidNumber': gid,
            'homeDirectory': self._default(home, f'/home/{self.name}'),
            'userPassword': self._hash_password(password),
            'gecos': gecos,
            'loginShell': shell,
        }

        self._add(attrs)
        return self

    def modify(
        self,
        *,
        uid: int | LDAP.Flags | None = None,
        gid: int | LDAP.Flags | None = None,
        password: str | LDAP.Flags | None = None,
        home: str | LDAP.Flags | None = None,
        gecos: str | LDAP.Flags | None = None,
        shell: str | LDAP.Flags | None = None,
    ) -> LDAPUser:
        attrs = {
            'uidNumber': uid,
            'gidNumber': gid,
            'homeDirectory': home,
            'userPassword': self._hash_password(password),
            'gecos': gecos,
            'loginShell': shell,
        }

        self._set(attrs)
        return self


class LDAPGroup(LDAPObject):
    def __init__(
        self,
        role: LDAP,
        name: str,
        basedn: LDAPObject | str | None = None,
        *,
        rfc2307bis: bool = False
    ) -> None:
        super().__init__(role, f'cn={name}', basedn)
        self.name = name
        self.rfc2307bis = rfc2307bis

        if not self.rfc2307bis:
            self.object_class = ['posixGroup']
            self.member_attr = 'memberUid'
        else:
            self.object_class = ['posixGroup', 'groupOfNames']
            self.member_attr = 'member'

    def __members(self, values: list[LDAPUser | LDAPGroup | str]) -> list[str] | None:
        if values is None:
            return None

        if self.rfc2307bis:
            return [x.dn if isinstance(x, LDAPObject) else self.role.dn(x) for x in values]

        return [x.name if isinstance(x, LDAPObject) else x for x in values]

    def add(
        self,
        *,
        gid: int | None = None,
        members: list[LDAPUser | LDAPGroup | str] | None = None,
        password: str | None = None,
        description: str | None = None,
    ) -> LDAPGroup:
        # Assign gid automatically if not present to have the same
        # interface as other services.
        if gid is None:
            gid = self.role._generate_gid()

        attrs = {
            'objectClass': self.object_class,
            'cn': self.name,
            'gidNumber': gid,
            'userPassword': self._hash_password(password),
            'description': description,
            self.member_attr: self.__members(members),
        }

        self._add(attrs)
        return self

    def modify(
        self,
        *,
        gid: int | LDAP.Flags | None = None,
        members: list[LDAPUser | LDAPGroup | str] | LDAP.Flags | None = None,
        password: str | LDAP.Flags | None = None,
        description: str | LDAP.Flags | None = None,
    ) -> LDAPGroup:
        attrs = {
            'gidNumber': gid,
            'userPassword': self._hash_password(password),
            'description': description,
            self.member_attr: self.__members(members),
        }

        self._set(attrs)
        return self

    def add_member(self, member: LDAPUser | LDAPGroup | str) -> LDAPGroup:
        return self.add_members([member])

    def add_members(self, members: list[LDAPUser | LDAPGroup | str]) -> LDAPGroup:
        self._modify(add={self.member_attr: self.__members(members)})
        return self

    def remove_member(self, member: LDAPUser | LDAPGroup | str) -> LDAPGroup:
        return self.remove_members([member])

    def remove_members(self, members: list[LDAPUser | LDAPGroup | str]) -> LDAPGroup:
        self._modify(delete={self.member_attr: self.__members(members)})
        return self
