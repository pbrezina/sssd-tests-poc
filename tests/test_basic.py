import pytest

from lib.multihost import KnownTopology, Multihost, Topology, TopologyDomain
from lib.multihost.roles import AD, IPA, LDAP, Client, GenericAD, GenericProvider, Samba


@pytest.mark.topology('client', Topology(TopologyDomain('sssd', client=1)))
def test_mh(mh: Multihost):
    assert mh.sssd.client[0].role == 'client'


@pytest.mark.topology('client', Topology(TopologyDomain('sssd', client=1)), client='sssd.client[0]')
def test_fixture_name(client: Client):
    assert client.role == 'client'


@pytest.mark.topology(KnownTopology.Client)
def test_client(client: Client):
    assert client.role == 'client'


@pytest.mark.topology(KnownTopology.LDAP)
def test_ldap(client: Client, ldap: LDAP):
    assert client.role == 'client'
    assert ldap.role == 'ldap'


@pytest.mark.topology(KnownTopology.IPA)
def test_ipa(client: Client, ipa: IPA):
    assert client.role == 'client'
    assert ipa.role == 'ipa'


@pytest.mark.topology(KnownTopology.AD)
def test_ad(client: Client, ad: AD):
    assert client.role == 'client'
    assert ad.role == 'ad'


@pytest.mark.topology(KnownTopology.Samba)
def test_samba(client: Client, samba: Samba):
    assert client.role == 'client'
    assert samba.role == 'samba'


@pytest.mark.topology(KnownTopology.AD)
@pytest.mark.topology(KnownTopology.Samba)
def test_any_ad(client: Client, provider: GenericAD):
    assert True


@pytest.mark.topology(KnownTopology.LDAP)
@pytest.mark.topology(KnownTopology.IPA)
@pytest.mark.topology(KnownTopology.AD)
@pytest.mark.topology(KnownTopology.Samba)
def test_generic_provider(client: Client, provider: GenericProvider):
    # provider.add_user(name='my_user', uid=1000, gid=1000)
    # result = client.id('my_user')
    # assert result.name == 'my_user'
    # assert result.uid == 1000
    # assert result.gid == 1000
    # assert provider.role == 'ipa'
    assert True


@pytest.mark.parametrize('test', [1, 2])
@pytest.mark.topology(KnownTopology.LDAP)
@pytest.mark.topology(KnownTopology.IPA)
@pytest.mark.topology(KnownTopology.AD)
@pytest.mark.topology(KnownTopology.Samba)
def test_parametrize(client: Client, provider: GenericProvider, test: int):
    assert True
