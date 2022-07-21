from __future__ import annotations

from ..host import BaseHost
from .base import MultihostUtility


class HostAuthentication(MultihostUtility):
    """
    Remote host authentication.

    Provides helpers to test authentication on remote host via su, sudo and ssh.
    """

    def __init__(self, host: BaseHost) -> None:
        """
        :param host: Remote host.
        :type host: BaseHost
        """
        super().__init__(host)

        self.su: HostSU = HostSU(host)
        """
        Interface to su command.
        """

        self.sudo: HostSudo = HostSudo(host)
        """
        Interface to sudo command.
        """

        self.ssh: HostSSH = HostSSH(host)
        """
        Interface to ssh command.
        """


class AuthBase(MultihostUtility):
    """
    Base class for authentication tools.
    """

    def _expect(self, script: str) -> int:
        """
        Execute expect script and return its return code.

        :param script: Expect script.
        :type script: str
        :return: Expect return code.
        :rtype: int
        """
        result = self.host.exec('su --shell /bin/sh nobody -c "/bin/expect -d"', stdin=script, raise_on_error=False)
        return result.rc


class HostSU(AuthBase):
    """
    Interface to su command.
    """

    def password(self, username: str, password: str) -> bool:
        """
        Call ``su - $username`` and authenticate the user with password.

        :param name: User name.
        :type name: str
        :param password: User password.
        :type password: str
        :return: True if authentication was successful, False otherwise.
        :rtype: bool
        """

        rc = self._expect(rf"""
            # It takes some time to get authentication failure
            set timeout 10
            set prompt "\n.*\[#\$>\] $"

            spawn su - "{username}"

            expect {{
                "Password:" {{send "{password}\n"}}
                timeout {{puts "expect result: Unexpected su output"; exit 1}}
                eof {{puts "expect result: Unexpected end of file"; exit 2}}
            }}

            expect {{
                -re $prompt {{puts "expect result: Password authentication successful"; exit 0}}
                "Authentication failure" {{puts "expect result: Authentication failure"; exit 4}}
                timeout {{puts "expect result: Unexpected su output"; exit 1}}
                eof {{puts "expect result: Unexpected end of file"; exit 2}}
            }}

            puts "expect result: Unexpected code path"
            exit 3
        """)

        return rc == 0


class HostSudo(AuthBase):
    """
    Interface to sudo command.
    """

    def list(self, username: str, password: str = None) -> bool:
        result = self.host.exec(f'su - "{username}" -c "sudo --stdin -l"', stdin=password, raise_on_error=False)

        return result.rc == 0


class HostSSH(AuthBase):
    """
    Interface to ssh command.
    """

    def __init__(self, host: BaseHost) -> None:
        super().__init__(host)

        self.opts = '-o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no'

    def password(self, username: str, password: str) -> bool:
        """
        SSH to the remote host and authenticate the user with password.

        :param name: User name.
        :type name: str
        :param password: User password.
        :type password: str
        :return: True if authentication was successful, False otherwise.
        :rtype: bool
        """

        rc = self._expect(rf"""
            # It takes some time to get authentication failure
            set timeout 10
            set prompt "\n.*\[#\$>\] $"

            spawn ssh {self.opts} -o PreferredAuthentications=password -o NumberOfPasswordPrompts=1 -l "{username}" localhost

            expect {{
                "password:" {{send "{password}\n"}}
                timeout {{puts "expect result: Unexpected su output"; exit 1}}
                eof {{puts "expect result: Unexpected end of file"; exit 2}}
            }}

            expect {{
                -re $prompt {{puts "expect result: Password authentication successful"; exit 0}}
                "Permission denied" {{puts "expect result: Authentication failure"; exit 4}}
                timeout {{puts "expect result: Unexpected su output"; exit 1}}
                eof {{puts "expect result: Unexpected end of file"; exit 2}}
            }}

            puts "expect result: Unexpected code path"
            exit 3
        """)

        return rc == 0
