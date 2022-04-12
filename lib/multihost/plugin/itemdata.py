from typing import Optional

import pytest

from .markers import TopologyMarker


class MultihostItemData(object):
    def __init__(self, item: pytest.Item) -> None:
        self.topology = self._topology(item)

    def _topology(self, item: pytest.Item) -> Optional[TopologyMarker]:
        mark = item.get_closest_marker(name='topology')
        if mark is None:
            return None

        return TopologyMarker(*mark.args, **mark.kwargs)
