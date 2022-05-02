import pytest

from lib.multihost import Multihost, Topology, Topologies, TopologyDomain
from lib.multihost.roles import AD, IPA, LDAP, Client


@pytest.mark.topology(Topologies.Client)
def test_client(client: Client):
    assert client.role == 'client'


@pytest.mark.topology(Topologies.LDAP)
def test_ldap(client: Client, ldap: LDAP):
    assert client.role == 'client'
    assert ldap.role == 'ldap'


@pytest.mark.topology(Topologies.IPA)
def test_ipa(client: Client, ipa: IPA):
    assert client.role == 'client'
    assert ipa.role == 'ipa'


@pytest.mark.topology(Topologies.AD)
def test_ad(client: Client, ad: AD):
    assert client.role == 'client'
    assert ad.role == 'ad'


@pytest.mark.topology(Topologies.Client)
def test_mh(mh: Multihost):
    assert mh.sssd.client[0].role == 'client'


# @pytest.mark.topology(TopologyDomain('sssd', client=1))
# def test_default_name(sssd_client_0: Client):
#     assert sssd_client_0.role == 'client'


# @pytest.mark.topology(TopologyDomain('sssd', client=1), {'sssd_client_0': 'myclient'})
# def test_custom_name(myclient: Client):
#     assert myclient.role == 'client'


# @pytest.mark.tier(0)
# @pytest.mark.topology(Topology.LDAP)
# @pytest.mark.topology(Topology.IPA)
# @pytest.mark.topology(Topology.AD)
# def test_parametrize_provider(client: Client, provider: CommonProvider):
#     provider.add_user(name='my_user', uid=1000, gid=1000)
#     result = client.id('my_user')
#     assert result.name == 'my_user'
#     assert result.uid == 1000
#     assert result.gid == 1000
