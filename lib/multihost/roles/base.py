from __future__ import annotations

import pathlib
from enum import Enum, auto
from typing import TYPE_CHECKING

from ..host import BaseHost
from ..utils.authselect import HostAuthselect
from ..utils.base import MultihostUtility
from ..utils.fs import HostFileSystem
from ..utils.service import HostService

if TYPE_CHECKING:
    from ..multihost import Multihost


class BaseRole(object):
    """
    Base role class. Roles are the main interface to the remote hosts that can
    be directly accessed in test cases as fixtures.

    All changes to the remote host that were done through the role object API
    are automatically reverted when a test is finished.
    """

    class Flags(Enum):
        DELETE = auto()
        """
        Delete attribute when modifying object.
        """

    def __init__(self, mh: Multihost, role: str, host: BaseHost) -> None:
        self.mh = mh
        self.role = role
        self.host = host

    def setup(self) -> None:
        """
        Setup all :class:`lib.multihost.utils.base.MultihostUtility` objects
        that are attributes of this class.

        :meta private:
        """
        MultihostUtility.SetupUtilityAttributes(self)

    def teardown(self) -> None:
        """
        Teardown all :class:`lib.multihost.utils.base.MultihostUtility` objects
        that are attributes of this class.

        :meta private:
        """
        MultihostUtility.TeardownUtilityAttributes(self)

    def collect_artifacts() -> None:
        """
        Collect test artifacts.

        :meta private:
        """
        pass


class BaseObject(object):
    """
    Base class for service object management like users and groups. This class
    provide helper functions to parse output and build command line arguments.
    """

    class cli(Enum):
        """
        Command line parameter types.
        """

        PLAIN = auto()
        """
        Use plain parameter value without any modification.
        """

        VALUE = auto()
        """
        Use parameter value but enclose it in quotes in script mode.
        """

        SWITCH = auto()
        """
        Parameter is a switch which is enabled if value is True.
        """

        POSITIONAL = auto()
        """
        Parameter is a positional argument.
        """

    def __init__(self, cli_prefix: str = '--') -> None:
        """
        :param cli_prefix: Command line option prefix, defaults to '--'
        :type cli_prefix: str, optional
        """
        self._cli_prefix = cli_prefix

    def _build_args(self, attrs: dict[str, tuple[BaseObject.cli, any]], as_script: bool = False) -> list[str] | str:
        """
        Build command line arguments.

        Parameters are passed in :attr:`attrs` which is a dictionary. The key is
        name of the command line argument and the value is a tuple of ``(type,
        value)``. The value is converted to string. If no value is given, that
        is if ``value`` is ``None``, then it is omitted.

        .. code-block:: python
            :caption: Example usage

            attrs = {
                'uid': (self.cli.VALUE, uid),
                'password': (self.cli.SWITCH, True) if password is not None else None,
                ...
            }

            args = self._build_args(attrs)

        :param attrs: Command line parameters.
        :type attrs: dict[str, tuple[BaseObject.cli, any]]
        :param as_script: Return string instead of list of arguments, defaults to False
        :type as_script: bool, optional
        :return: List of as_script (exec style) or string to be used in scripts.
        :rtype: list[str]
        """
        def encode_value(value):
            return str(value) if not as_script else f"'{value}'"

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

        if as_script:
            return ' '.join(args)

        return args

    def _parse_attrs(self, lines: list[str], attrs: list[str] | None = None) -> dict[str, list[str]]:
        """
        Parse LDAP attributes from output.

        :param lines: Output.
        :type lines: list[str]
        :param attrs: If set, only requested attributes are returned, defaults to None
        :type attrs: list[str] | None, optional
        :return: Dictionary with attribute name as a key.
        :rtype: dict[str, list[str]]
        """
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
    """
    Base linux role.
    """

    def __init__(self, mh: Multihost, role: str, host: BaseHost) -> None:
        super().__init__(mh, role, host)

        self.authselect: HostAuthselect = HostAuthselect(host)
        """
        Manage nsswitch and PAM configuration.
        """

        self.fs: HostFileSystem = HostFileSystem(host)
        """
        File system manipulation.
        """

        self.svc: HostService = HostService(host)
        """
        Systemd service management.
        """

    def collect_artifacts(self) -> None:
        """
        Collect test artifacts that were requested by the multihost configuration.

        :meta private:
        """
        dir = self.mh.request.config.getoption("artifacts_dir")
        mode = self.mh.request.config.getoption("collect_artifacts")
        if mode == 'never' or (mode == 'on-failure' and self.mh.data.outcome != 'failed'):
            return

        artifacts = self.host.config.get('artifacts', [])
        if not artifacts:
            return

        # Create output directory
        path = f'{dir}/{self.mh.request.node.name}'
        pathlib.Path(path).mkdir(parents=True, exist_ok=True)

        # Fetch artifacts
        self.fs.download_files(artifacts, f'{path}/{self.role}_{self.host.hostname}.tgz')


class WindowsRole(BaseRole):
    """
    Base Windows role.
    """
    pass
