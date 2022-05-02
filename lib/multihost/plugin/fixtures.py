import pytest

from .itemdata import MultihostItemData
from ..config import MultihostConfig
from ..multihost import Multihost


@pytest.fixture(scope='function')
def mh(request: pytest.FixtureRequest, multihost: MultihostConfig):
    data: MultihostItemData = request.node.multihost
    with Multihost(multihost, scope=data.topology_mark.topology) as mh:
        yield mh
