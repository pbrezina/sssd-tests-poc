Writing new test
################

This article talks about extensions specific to our tests. In order to learn
pytest details, please visit the `pytest documentation`_.

.. _pytest documentation: https://docs.pytest.org

Using the topology marker
*************************

Each test that requires access to hosts defined in multihost configuration must
be marked with a ``topology`` marker. This marker provides information about the
topology that is required to run the test and defines fixture mapping between a
short fixture name and a host from the multihost configuration (this is
explained later in `Deep dive into multihost fixtures`_).

The marker is used as:

.. code-block:: python

    import pytest


    @pytest.mark.topology(name, topology, fixtures ...)
    def test_example():
        assert True

Where ``name`` is the human-readable topology name that is visible in ``pytest``
verbose output, you can also use this name to filter tests that you want to run
(with the ``-k`` parameter). The next argument, ``topology``, is instance of
:class:`lib.multihost.Topology` and then follows keyword arguments as a fixture
mapping - we will cover that later.

.. seealso::

    You can read more about the topology marker at :mod:`lib.multihost.plugin`,
    specifically at :class:`lib.multihost.plugin.TopologyMark`. It is also worth
    to read the complete documentation of :mod:`lib.multihost` module.

There is a number of predefined topologies in
:class:`lib.multihost.KnownTopology` that can be used directly as the topology
marker argument. It is recommended to use this instead of providing your own
topology unless it is really necessary.

.. code-block:: python

    import pytest

    from lib.multihost import KnownTopology
    from lib.multihost.roles import Client, LDAP


    @pytest.mark.topology(KnownTopology.LDAP)
    def test_example(client: Client, ldap: LDAP):
        assert True

The example above already uses the fixture mapping mentioned earlier. It uses
the fixture ``client`` that points to the client host and ``ldap`` that can be
used to manipulate with the host that provides the ldap role. This is thoroughly
covered in the next section.

Deep dive into multihost fixtures
*********************************

The previous example showed how to use :attr:`KnownTopology.LDAP` to define the
required topology and provide ``client`` and ``ldap`` fixture. This section
described the mechanics underneath so you can correctly write your own tests.

Defining a topology
===================

Simply put, topology defines the requirements that must be matched by multihost
configuration in order to run the selected test. If the requirements are not
fulfilled, the test is omitted.

The requirements are:

* How many domains are needed
* What domain types are needed
* How many hosts of specific role are needed inside a domain

For example the following topology (written in yaml) requires one domain of type
``sssd`` and the domain must contain one host that has the ``client`` role and
one host that has the ``ldap`` role.

.. code-block:: yaml

    - type: sssd
      hosts:
        client: 1
        ldap: 1

There are :class:`lib.multihost.Topology` and :class:`lib.multihost.TopologyDomain`
that you can use to put it in the code:

.. code-block:: python

    Topology(
        TopologyDomain('sssd', client=1, ldap=1)
    )

Using the mh fixture
====================

The :func:`lib.multihost.plugin.mh` fixture is a fixture that is always
available to a test that is marked with the topology marker. It provides access
to domains by type and to hosts by role. Each host object is created as an
instance of specific :mod:`lib.multihost.roles`.

We can use this fixture to access either group of hosts with
``mh.$domain-type.$role`` or individual host with
``mh.$domain-type.$role[$index]``. The following snippet shows how to access the
hosts from our example topology.

.. code-block:: python

    import pytest

    from lib.multihost import Multihost, Topology, TopologyDomain


    @pytest.mark.topology('ldap', Topology(TopologyDomain('sssd', client=1, ldap=1)))
    def test_example(mh: Multihost):
        assert mh.sssd.client[0].role == 'client'
        assert mh.sssd.ldap[0].role == 'ldap'

We can also use advantage of Python type hints to let our editor provide us code
suggestions.

.. code-block:: python

    import pytest

    from lib.multihost import Multihost, Topology, TopologyDomain
    from lib.multihost.roles import Client, LDAP


    @pytest.mark.topology('ldap', Topology(TopologyDomain('sssd', client=1, ldap=1)))
    def test_example(mh: Multihost):
        client: Client = mh.sssd.client[0]
        ldap: LDAP = mh.sssd.ldap[0]

        assert client.role == 'client'
        assert ldap.role == 'ldap'

Once the test run is finished, this fixture automatically initiates a teardown
process that rollbacks any change done on the remote host.

.. warning::

    Using the ``mh`` fixture directly is not recommended. Please see
    `Using dynamic fixtures`_ to learn how to avoid using this fixture by
    creating a fixture mapping.

Using dynamic fixtures
======================

The topology marker allows us to create a mapping between our own fixture name
and specific path inside the ``mh`` fixture by providing additional keyword-only
arguments to the marker.

The example above can be rewritten as:

.. code-block:: python
    :emphasize-lines: 9

    import pytest

    from lib.multihost import Topology, TopologyDomain
    from lib.multihost.roles import Client, LDAP


    @pytest.mark.topology(
        'ldap', Topology(TopologyDomain('sssd', client=1, ldap=1)),
        client='sssd.client[0]', ldap='sssd.ldap[0]'
    )
    def test_example(client: Client, ldap: LDAP):
        assert client.role == 'client'
        assert ldap.role == 'ldap'

By adding the fixture mapping, we tell :mod:`lib.multihost.plugin` to
dynamically create ``client`` and ``ldap`` fixtures for the test run and set it
to the value of individual hosts inside the ``mh`` fixture which is still used
under the hood.

We can also make a fixture for a group of hosts if our test would benefit from
it.

.. code-block:: python
    :emphasize-lines: 9

    import pytest

    from lib.multihost import Topology, TopologyDomain
    from lib.multihost.roles import Client


    @pytest.mark.topology(
        'ldap', Topology(TopologyDomain('sssd', client=1, ldap=1)),
        clients='sssd.client'
    )
    def test_example(clients: list[Client]):
        for client in clients:
            assert client.role == 'client'

.. note::

    We don't have to provide mapping for every single host, it is up to us
    which hosts will be used. It is even possible to combine fixture mapping
    and at the same time use ``mh`` fixture as well:

    .. code-block:: python

        def test_example(mh: Multihost, clients: list[Client])

    It is also possible to request multiple fixtures for a single host. This
    can be used in test parametrization as we will see later.

    .. code-block:: python
        :emphasize-lines: 3

        @pytest.mark.topology(
            'ldap', Topology(TopologyDomain('sssd', client=1, ldap=1)),
            ldap='sssd.ldap[0]', provider='sssd.ldap[0]'
        )

.. warning::

    Creating custom topologies and fixture mapping is not recommended and should
    be used only when it is really needed. See the following section `Using
    known topologies`_ to learn how to use predefined topologies in order to
    shorten the code and provide naming consistency across all tests.

Using known topologies
======================

This article already covered lots of ways of achieving the same thing to show
how the plugin works. This section now describes the **recommended** usage by
introducing :class:`lib.multihost.KnownTopology` class.

This class provides predefined :class:`lib.multihost.plugin.TopologyMark` that
can be used directly as parameter to the topology marker. Under the hood, it
is the very same thing that was already explained.

The topology from previous examples is simply
:attr:`lib.multihost.KnownTopology.LDAP`. And we can use it like:

.. code-block:: python
    :emphasize-lines: 7

    import pytest

    from lib.multihost import KnownTopology
    from lib.multihost.roles import Client, LDAP


    @pytest.mark.topology(KnownTopology.LDAP)
    def test_example(client: Client, ldap: LDAP):
        assert client.role == 'client'
        assert ldap.role == 'ldap'

.. note::

    If you get to a point when existing topologies are not enough, feel free
    to define a new one inside :class:`lib.multihost.KnownTopology` and use
    the new entry so it can be reused later by other test when needed.

Topology parametrization
************************

We can run single test against multiple SSSD providers by topology
parametrization. This is achieved by assigning multiple topology markers to
single test.

.. code-block:: python

    import pytest

    from lib.multihost import KnownTopology
    from lib.multihost.roles import Client, LDAP

    @pytest.mark.topology(KnownTopology.LDAP)
    @pytest.mark.topology(KnownTopology.IPA)
    @pytest.mark.topology(KnownTopology.AD)
    @pytest.mark.topology(KnownTopology.Samba)
    def test_example(client: Client, provider: GenericProvider):
        assert True

Now, if we run the test, we can see that it was executed multiple times and each
time with different topology therefore the ``provider`` points to the expected
host (``sssd.ldap[0]`` for ldap, ``sssd.ipa[0]`` for ipa etc.).

.. code-block:: console

    $ pytest --multihost-config mhc.yaml -k test_example -v
    ...
    tests/test_basic.py::test_example (samba) PASSED                                                                                                                                                                                [ 12%]
    tests/test_basic.py::test_example (ad) PASSED                                                                                                                                                                                   [ 25%]
    tests/test_basic.py::test_example (ipa) PASSED                                                                                                                                                                                  [ 37%]
    tests/test_basic.py::test_example (ldap) PASSED
    ...

This is internally achieved by providing two fixtures for the server host. We
can look at how :attr:`lib.multihost.KnownTopology.LDAP` is defined to see an
example:

.. code-block:: python
    :emphasize-lines: 4

    LDAP = TopologyMark(
        name='ldap',
        topology=Topology(TopologyDomain('sssd', client=1, ldap=1)),
        fixtures=dict(client='sssd.client[0]', ldap='sssd.ldap[0]', provider='sssd.ldap[0]')
    )

We can go even further and use ``@pytest.mark.parametrize`` to test against
multiple values.

.. code-block:: python
    :emphasize-lines: 6

    import pytest

    from lib.multihost import KnownTopology
    from lib.multihost.roles import Client, LDAP

    @pytest.mark.parametrize('mockvalue', [1, 2])
    @pytest.mark.topology(KnownTopology.LDAP)
    @pytest.mark.topology(KnownTopology.IPA)
    @pytest.mark.topology(KnownTopology.AD)
    @pytest.mark.topology(KnownTopology.Samba)
    def test_example(client: Client, provider: GenericProvider, mockvalue: int):
        assert True


Now the test is run for each topology twice, once with ``mockvalue=1`` and the
second time with ``mockvalue=2``.

.. code-block:: console

    $ pytest --multihost-config mhc.yaml -k test_example -v
    ...
    tests/test_basic.py::test_example[1] (samba) PASSED                                                                                                                                                                                [ 12%]
    tests/test_basic.py::test_example[1] (ad) PASSED                                                                                                                                                                                   [ 25%]
    tests/test_basic.py::test_example[1] (ipa) PASSED                                                                                                                                                                                  [ 37%]
    tests/test_basic.py::test_example[1] (ldap) PASSED                                                                                                                                                                                 [ 50%]
    tests/test_basic.py::test_example[2] (samba) PASSED                                                                                                                                                                                [ 62%]
    tests/test_basic.py::test_example[2] (ad) PASSED                                                                                                                                                                                   [ 75%]
    tests/test_basic.py::test_example[2] (ipa) PASSED                                                                                                                                                                                  [ 87%]
    tests/test_basic.py::test_example[2] (ldap) PASSED
    ...
