from __future__ import annotations

import pytest

from ..config import MultihostConfig
from ..multihost import Multihost
from .plugin import MultihostItemData


@pytest.fixture(scope="session")
def multihost(request: pytest.FixtureRequest) -> MultihostConfig:
    """
    Legacy multihost fixture to allow running legacy tests.

    .. warning::

        This fixture is deprecated in favor of :func:`mh` and dynamic fixtures.
        It must not be used in new tests.

    :param request: Pytest's ``request`` fixture.
    :type request: pytest.FixtureRequest
    :return: Legacy multihost object.
    :rtype: MultihostConfig
    """

    # TODO: return QaClass objects
    data:  MultihostItemData = request.node.multihost
    return data.multihost


@pytest.fixture(scope='function')
def mh(request: pytest.FixtureRequest) -> Multihost:
    """
    Pytest fixture. Returns instance of :class:`Multihost`. When a pytest test
    is finished, this fixture takes care of tearing down the :class:`Multihost`
    object automatically in order to clean up after the test run.

    .. note::

        It is preferred that the test case does not use this fixture directly
        but rather access the hosts through dynamically created role fixtures
        that are defined in ``@pytest.mark.topology``.

    :param request: Pytest's ``request`` fixture.
    :type request: pytest.FixtureRequest
    :raises ValueError: If not multihost configuration was given.
    :yield: lib.multihost.Multihost
    """

    data:  MultihostItemData = request.node.multihost
    if data is None:
        nodeid = f'{request.node.parent.nodeid}::{request.node.originalname}'
        raise ValueError(f'{nodeid}: mh fixture requested but no multihost configuration was provided')

    with Multihost(request, data.multihost, data.topology_mark.topology) as mh:
        yield mh
