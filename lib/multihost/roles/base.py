from pytest_multihost.host import BaseHost


class BaseRole(object):
    def __init__(self, role: str, host: BaseHost) -> None:
        self.role = role
        self.host = host

    def teardown(self) -> None:
        pass


class Client(BaseRole):
    def __init__(self, role: str, host: BaseHost) -> None:
        super().__init__(role, host)
        self.i_am_client = True


class LDAP(BaseRole):
    def __init__(self, role: str, host: BaseHost) -> None:
        super().__init__(role, host)
        self.i_am_ldap = True


class IPA(BaseRole):
    def __init__(self, role: str, host: BaseHost) -> None:
        super().__init__(role, host)
        self.i_am_ipa = True


class AD(BaseRole):
    def __init__(self, role: str, host: BaseHost) -> None:
        super().__init__(role, host)
        self.i_am_ad = True
