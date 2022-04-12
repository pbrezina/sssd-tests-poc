from pytest_multihost.host import BaseHost


class BaseRole(object):
    def __init__(self, role: str, host: BaseHost) -> None:
        self.role = role
        self.host = host

    def teardown(self) -> None:
        pass


class GenericProvider(BaseRole):
    def __init__(self, role: str, host: BaseHost) -> None:
        super().__init__(role, host)


class GenericAD(BaseRole):
    def __init__(self, role: str, host: BaseHost) -> None:
        super().__init__(role, host)


class Client(BaseRole):
    def __init__(self, role: str, host: BaseHost) -> None:
        super().__init__(role, host)


class LDAP(BaseRole):
    def __init__(self, role: str, host: BaseHost) -> None:
        super().__init__(role, host)


class IPA(BaseRole):
    def __init__(self, role: str, host: BaseHost) -> None:
        super().__init__(role, host)


class AD(BaseRole):
    def __init__(self, role: str, host: BaseHost) -> None:
        super().__init__(role, host)


class Samba(BaseRole):
    def __init__(self, role: str, host: BaseHost) -> None:
        super().__init__(role, host)
