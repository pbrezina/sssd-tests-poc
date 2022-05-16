from __future__ import annotations

from .ad import AD
from .base import BaseRole, LinuxRole, WindowsRole
from .client import Client
from .generic import GenericADProvider, GenericProvider
from .ipa import IPA
from .ldap import LDAP
from .samba import Samba

__all__ = [
    "AD",
    "BaseRole",
    "Client",
    "GenericADProvider",
    "GenericProvider",
    "IPA",
    "LDAP",
    "LinuxRole",
    "Samba",
    "WindowsRole",
]


def get_role_class(role: str) -> type[BaseRole]:
    mapping = {
        'client': Client,
        'ad': AD,
        'ipa': IPA,
        'ldap': LDAP,
        'samba': Samba
    }

    if role not in mapping:
        raise ValueError(f'Unexpected role: {role}')

    return mapping[role]
