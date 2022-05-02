from typing import Optional

import pytest

from .marks import TopologyMark
from ..config import MultihostConfig
from ..topology import Topologies


class MultihostItemData(object):
    def __init__(self, item: pytest.Item, multihost: MultihostConfig) -> None:
        self.multihost = multihost
        self.topology_mark = self._topology_mark(item)

    def _topology_mark(self, item: pytest.Item) -> Optional[TopologyMark]:
        mark = item.get_closest_marker(name='topology')
        if mark is None:
            return None

        if not mark.args:
            raise ValueError('Invalid topology mark, no values specified')

        args = mark.args[0].value if isinstance(mark.args[0], Topologies) else mark.args
        return TopologyMark(*args, **mark.kwargs)
