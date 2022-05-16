from __future__ import annotations

from pytest_multihost.transport import Command


class RemoteCommandResult(object):
    """
    Remote command result.
    """

    def __init__(self, command: Command) -> None:
        """
        :param command: A pytest_multihost command object.
        :type command: pytest_multihost.transport.Command
        """

        self.command = command

        self.rc: int = None
        """
        Return code.
        """

        self.stdout: str = None
        """
        Standard output as string.
        """

        self.stdout_lines: list[str] = None
        """
        Standard output as list of lines.
        """

        self.stderr: str = None
        """
        Standard error output as string.
        """

        self.stderr_lines: list[str] = None
        """
        Standard error output as list of lines.
        """

        self.__set_result(command)

    def __set_result(self, result: Command):
        self.rc = result.returncode
        self.stdout: str = result.stdout_text
        self.stdout_lines: list[str] = self.stdout.splitlines()
        self.stderr: str = result.stderr_text
        self.stderr_lines: list[str] = self.stderr.splitlines()
        self._parse_result()

    def _parse_result(self):
        pass

    def wait(self, raise_on_error: bool | None = True) -> int:
        """
        Wait for the command to finish.

        :param raise_on_error: Raise ``subprocess.CalledProcessError`` on
            non-zero return code, defaults to ``None`` (use current setting of the
            command)
        :type raise_on_error: bool, optional
        :return: Return code.
        :rtype: int
        """

        if raise_on_error is None:
            raise_on_error = self.command.raiseonerr

        self.command.wait(raiseonerr=raise_on_error)
        self.__set_result()
        return self.rc

    def __enter__(self):
        return self.command.__enter__()

    def __exit__(self, *exc_info):
        self.wait(raise_on_error=None)
