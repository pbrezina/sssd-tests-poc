"""
Pytest multihost plugin. The main functionality is to make sure that only tests
that can be run using the given multihost configuration are executed.

.. note::

    This plugin is a high level wrapper around ``pytest_multihost`` with
    additional functionality.

New command line options
========================

* ``--multihost-log-path``: multihost logs will be printed to this file, use
  ``/dev/stdout`` if you want to print them to standard output (default: none)
* ``--collect-artifacts``: ``never`` (never collect artifacts), ``on-failure``
  (only collect artifacts for failed test run), ``always`` (collect artifacts
  even for successful run), default: ``on-failure``
* ``--artifacts-dir``: output directory for artifacts, default ``./artifacts``
* ``--exact-topology``: if set only test the require exactly the multihost
  configuration that was given are run (default: false)

  .. code-block:: console

      pytest --exact-topology --multihost-log-path ./test.log --multihost-config
      mhc.yaml

New markers
===========

* ``@pytest.mark.topology``

  .. code-block:: python

      @pytest.mark.topology(name: str, topology:
      lib.multihost.topology.Topology, /, *, fixture1=target1, ...)

New fixtures
============

* :func:`mh`
* :func:`multihost`

New functionality
=================

* filter tests using ``@pytest.mark.topology`` and
  :class:`lib.multihost.plugin.TopologyMark`
* run only tests which topology (as set by the ``topology`` marker) is satisfied
  by given multihost configuration
* dynamically create fixtures required by the test as defined in the
  ``topology`` marker
* parametrize tests by topology, each ``topology`` marker creates one test run
* automatically collect test run artifacts from remote hosts

.. raw:: html

   <hr>
"""

from __future__ import annotations

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
