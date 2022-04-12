import pytest
from pytest_multihost import make_multihost_fixture
from pytest_multihost.plugin import MultihostFixture

from .. import Multihost, Topology


@pytest.fixture(scope="session")
def multihost(request: pytest.FixtureRequest) -> MultihostFixture:
    plugin = request.config.pluginmanager.getplugin('MultihostPlugin')
    if not plugin:
        raise ValueError('Multihost plugin was not found')

    topology = Topology.FromMultihostConfig(plugin.confdict)

    yield make_multihost_fixture(
        request,
        descriptions=topology.describe(),
    )


@pytest.fixture(scope='function')
def mh(multihost: MultihostFixture):
    with Multihost(multihost) as mh:
        yield mh
