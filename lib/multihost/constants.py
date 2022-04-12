from enum import Enum, unique
from typing import final

from .plugin.marks import TopologyMark
from .topology import Topology, TopologyDomain


@final
@unique
class KnownTopology(Enum):
    """
    Well-known topologies that can be given to ``pytest.mark.topology``
    directly. It it expected to use these values in favor of providing
    custom marker values.

    .. code-block:: python
        :caption: Example usage

        @pytest.mark.topology(KnownTopology.LDAP)
        def test_ldap(client: Client, ldap: LDAP):
            assert True
    """

    Client = TopologyMark(
        name='client',
        topology=Topology(TopologyDomain('sssd', client=1)),
        fixtures=dict(client='sssd.client[0]')
    )
    """
    .. topology-mark:: KnownTopology.Client
    """

    LDAP = TopologyMark(
        name='ldap',
        topology=Topology(TopologyDomain('sssd', client=1, ldap=1)),
        fixtures=dict(client='sssd.client[0]', ldap='sssd.ldap[0]', provider='sssd.ldap[0]')
    )
    """
    .. topology-mark:: KnownTopology.LDAP
    """

    IPA = TopologyMark(
        name='ipa',
        topology=Topology(TopologyDomain('sssd', client=1, ipa=1)),
        fixtures=dict(client='sssd.client[0]', ipa='sssd.ipa[0]', provider='sssd.ipa[0]')
    )
    """
    .. topology-mark:: KnownTopology.IPA
    """

    AD = TopologyMark(
        name='ad',
        topology=Topology(TopologyDomain('sssd', client=1, ad=1)),
        fixtures=dict(client='sssd.client[0]', ad='sssd.ad[0]', provider='sssd.ad[0]')
    )
    """
    .. topology-mark:: KnownTopology.AD
    """

    Samba = TopologyMark(
        name='samba',
        topology=Topology(TopologyDomain('sssd', client=1, samba=1)),
        fixtures=dict(client='sssd.client[0]', samba='sssd.samba[0]', provider='sssd.samba[0]')
    )
    """
    .. topology-mark:: KnownTopology.Samba
    """
