from __future__ import annotations

from enum import Enum, auto
from typing import TYPE_CHECKING

from ..host import BaseHost
from ..utils.base import MultihostUtility
from ..utils.fs import HostFileSystem
from ..utils.service import HostService

if TYPE_CHECKING:
    from ..multihost import Multihost


class BaseRole(object):
    class Flags(Enum):
        DELETE = auto()

    def __init__(self, mh: Multihost, role: str, host: BaseHost) -> None:
        self.mh = mh
        self.role = role
        self.host = host

    def setup(self) -> None:
        MultihostUtility.SetupUtilityAttributes(self)

    def teardown(self) -> None:
        MultihostUtility.TeardownUtilityAttributes(self)


class BaseObject(object):
    class cli(Enum):
        PLAIN = auto()
        VALUE = auto()
        SWITCH = auto()
        POSITIONAL = auto()

    def __init__(self, cli_prefix: str = '--') -> None:
        self._cli_prefix = cli_prefix

    def _build_args(self, attrs: dict[str, tuple[BaseObject.cli, any]], quote: bool = False) -> list[str]:
        def encode_value(value):
            return str(value) if not quote else f"'{quote}'"

        args = []
        for key, item in attrs.items():
            if item is None:
                continue

            (type, value) = item
            if value is None:
                continue

            if type is self.cli.POSITIONAL:
                args.append(encode_value(value))
                continue

            if type is self.cli.SWITCH and value is True:
                args.append(self._cli_prefix + key)
                continue

            if type is self.cli.VALUE:
                args.append(self._cli_prefix + key)
                args.append(encode_value(value))
                continue

            if type is self.cli.PLAIN:
                args.append(self._cli_prefix + key)
                args.append(str(value))
                continue

            raise ValueError(f'Unknown option type: {type}')

        return args

    def _parse_attrs(self, lines: list[str], attrs: list[str] | None = None) -> dict[str, list[str]]:
        out = {}
        for line in lines:
            line = line.strip()
            if not line:
                continue

            (key, value) = map(lambda x: x.strip(), line.split(':', 1))
            if attrs is None or key in attrs:
                out.setdefault(key, [])
                out[key].append(value)

        return out


class LinuxRole(BaseRole):
    def __init__(self, mh: Multihost, role: str, host: BaseHost) -> None:
        super().__init__(mh, role, host)
        self.fs = HostFileSystem(host)
        self.svc = HostService(host)


class WindowsRole(BaseRole):
    pass
