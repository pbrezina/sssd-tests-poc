"""
Pytest multihost plugin. The main functionality is to make sure that only tests
that can be run using the given multihost configuration are executed.

.. note::

    This plugin is a high level wrapper around ``pytest_multihost`` with
    additional functionality.

New command line options
========================

* ``--exact-topology``: if set only test the require exactly the multihost
  configuration that was given are run

  .. code-block:: console

      pytest --exact-topology --multihost-config mhc.yaml

New markers
===========

* ``@pytest.mark.topology``

  .. code-block:: python

      @pytest.mark.topology(name: str, topology: lib.multihost.topology.Topology, /, *, fixture1=target1, ...)

New fixtures
============

* :func:`mh`
* :func:`multihost`

New functionality
=================

* filter tests using ``@pytest.mark.topology`` and :class:`lib.multihost.plugin.TopologyMark`
* run only tests which topology (as set by the ``topology`` marker) is satisfied by given multihost configuration
* dynamically create fixtures required by the test as defined in the ``topology`` marker
* parametrize tests by topology, each ``topology`` marker creates one test run

.. raw:: html

   <hr>
"""

from .fixtures import mh, multihost
from .marks import TopologyMark
from .plugin import pytest_addoption, pytest_configure

__all__ = [
    "mh",
    "multihost",
    "pytest_addoption",
    "pytest_configure",
    "TopologyMark",
]
