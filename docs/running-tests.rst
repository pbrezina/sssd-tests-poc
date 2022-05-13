Running tests
#############

Installing requirements
***********************

SSSD tests require using ``pytest`` and ``python_multihost`` pytest plugin. We
recommend to install the requirements inside Python virtual environment.

.. code-block:: console

    python3 -m venv .venv
    source .venv/bin/activate
    pip3 install -r ./requirements.txt

Setting up multihost environment
********************************

Even though our tests are run locally with ``pytest``, they actually run
commands on remote machines to make the setup more flexible and avoid changing
anything on your host. We will use the environment provided by
`sssd-ci-containers`_ in this example, however you can also setup your own
machines and provide custom multihost configuration.

.. _sssd-ci-containers: https://github.com/SSSD/sssd-ci-containers

Starting up CI containers
=========================

The following snippet is enough to get started. It will clone the
`sssd-ci-containers`_ project, install dependencies, setup dns and start the
containers. Please, follow instructions at `sssd-ci-containers`_ to get more
information.

.. code-block:: bash

    git clone https://github.com/SSSD/sssd-ci-containers.git
    cd sssd-ci-containers

    sudo dnf install -y podman podman-docker docker-compose
    sudo systemctl enable --now podman.socket
    sudo setsebool -P container_manage_cgroup true
    cp env.example .env

    sudo make setup-dns
    sudo make up

Creating multihost configuration
================================

Multihost configuration provides information about the domains and hosts that
will be used for testing SSSD. It describes what ``domains`` are available. Each
domain defines how many ``hosts`` are in the domain and each host provides or
implements given ``role``.

The following configuration can be used to test using the
``sssd-ci-containers``. You can just copy the content to ``mhc.yaml`` which we
use in the next examples.

.. code-block:: yaml

    root_password: 'Secret123'
    domains:
    - name: test
      type: sssd
      hosts:
      - name: client
        external_hostname: client.test
        role: client

      - name: ldap
        external_hostname: master.ldap.test
        role: ldap

      - name: ipa
        external_hostname: master.ipa.test
        role: ipa

      - name: samba
        external_hostname: dc.samba.test
        role: samba

Running tests
*************

Now, if you have setup the environment, you can run the tests with ``pytest``.

.. code-block:: console

    pytest --multihost-config mhc.yaml -v
