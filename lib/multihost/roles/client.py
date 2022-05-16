from __future__ import annotations

from typing import TYPE_CHECKING

from ..host import BaseHost
from ..utils.sssd import HostSSSD
from ..utils.tools import HostTools
from .base import LinuxRole

if TYPE_CHECKING:
    from ..multihost import Multihost


class Client(LinuxRole):
    def __init__(self, mh: Multihost, role: str, host: BaseHost) -> None:
        super().__init__(mh, role, host)
        self.sssd = HostSSSD(host, self.fs, self.svc, load_config=False)
        self.tools = HostTools(host)

    def setup(self) -> None:
        super().setup()
        self.sssd.stop()
        self.sssd.clear(db=True, logs=True, config=True)

        for domain, path in self.mh.data.topology_mark.domains.items():
            self.sssd.import_domain(domain, self.mh._lookup(path))
