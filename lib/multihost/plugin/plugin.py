import inspect
import logging
import sys
import textwrap

import pytest
import yaml

from .. import Topology
from .itemdata import MultihostItemData


class MultihostPlugin(object):
    def __init__(self, config: pytest.Config) -> None:
        self.logger = self._create_logger(config.option.verbose > 2)
        self.topology = None
        self.exact_topology = False

    @classmethod
    def GetLogger(cls) -> logging.Logger:
        return logging.getLogger('lib.multihost.plugin')

    def _create_logger(self, verbose) -> logging.Logger:
        stdout = logging.StreamHandler(sys.stdout)
        stdout.setLevel(logging.DEBUG)
        stdout.setFormatter(logging.Formatter('%(message)s'))

        logger = self.GetLogger()
        logger.addHandler(stdout)
        logger.setLevel(logging.DEBUG if verbose else logging.INFO)

        return logger

    @pytest.hookimpl(trylast=True)
    def pytest_sessionstart(self, session: pytest.Session) -> None:
        def bold(text: str) -> str:
            if sys.stdout.isatty():
                return f'\033[1m{text}\033[0m'

        pytest_multihost = session.config.pluginmanager.getplugin('MultihostPlugin')
        if not pytest_multihost:
            return

        self.exact_topology = session.config.getoption('exact_topology')
        self.topology = Topology.FromMultihostConfig(pytest_multihost.confdict)

        self.logger.info(bold('Multihost configuration:'))
        self.logger.info(textwrap.indent(yaml.dump(pytest_multihost.confdict), '  '))
        self.logger.info(bold('Detected topology:'))
        self.logger.info(textwrap.indent(yaml.dump(self.topology.describe()), '  '))
        self.logger.info(bold('Additional settings:'))
        self.logger.info(f'  require exact topology: {self.exact_topology}')
        self.logger.info('')

    @pytest.hookimpl(tryfirst=True)
    def pytest_collection_modifyitems(self, config: pytest.Config, items: list[pytest.Item]) -> None:
        selected = []
        deselected = []

        for item in items:
            item.multihost = MultihostItemData(item)

            if item.multihost.topology is not None:
                if self.exact_topology:
                    if item.multihost.topology.topology != self.topology:
                        deselected.append(item)
                        continue
                else:
                    if not item.multihost.topology.topology <= self.topology:
                        deselected.append(item)
                        continue

            selected.append(item)

        config.hook.pytest_deselected(items=deselected)
        items[:] = selected

    @pytest.hookimpl(tryfirst=True)
    def pytest_runtest_setup(self, item: pytest.Item) -> None:
        # Fill in parameters that will be set later in pytest_runtest_call hook,
        # otherwise pytest will raise unknown fixture error.
        if item.multihost.topology is not None:
            item.fixturenames.append('mh')
            spec = inspect.getfullargspec(item.obj)
            for arg in item.multihost.topology.args:
                if arg in spec.args:
                    item.funcargs[arg] = None

    @pytest.hookimpl(tryfirst=True)
    def pytest_runtest_call(self, item: pytest.Item) -> None:
        if item.multihost.topology is not None:
            item.multihost.topology.apply(item.funcargs['mh'], item.funcargs)


def pytest_addoption(parser):
    parser.addoption(
        "--exact-topology", action="store_true",
        help="Test will be deselected if its topology does not match multihost config exactly"
    )


def pytest_configure(config: pytest.Config):
    # register additional markers
    config.addinivalue_line(
        "markers", "topology(lib.multihost.topology.TopologyDomain, ...): topology required to run the test"
    )

    config.pluginmanager.register(MultihostPlugin(config))
