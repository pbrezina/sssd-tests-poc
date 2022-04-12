from __future__ import annotations

import base64
import textwrap

from ..host import BaseHost
from .base import MultihostUtility


class HostFileSystem(MultihostUtility):
    """
    Perform file system operations on remote host.

    All changes are automatically reverted when a test is finished.
    """

    def __init__(self, host: BaseHost) -> None:
        """
        :param host: Remote host instance.
        :type host: BaseHost
        """
        super().__init__(host)
        self.__rollback: list[str] = []

    def teardown(self):
        """
        Revert all file system changes.

        :meta private:
        """
        cmd = '\n'.join(reversed(self.__rollback))
        if cmd:
            self.host.exec(cmd)

        super().teardown()

    def mkdir(self, path: str, *, mode: str = None, user: str = None, group: str = None) -> None:
        """
        Create directory on remote host.

        :param path: Path of the directory.
        :type path: str
        :param mode: Access mode (chmod value), defaults to None
        :type mode: str, optional
        :param user: Owner, defaults to None
        :type user: str, optional
        :param group: Group, defaults to None
        :type group: str, optional
        :raises OSError: If directory can not be created.
        """
        cmd = f'''
        set -x

        mkdir '{path}'
        {self.__gen_chattrs(path, mode=mode, user=user, group=group)}
        '''

        result = self.host.exec(cmd, raise_on_error=False)
        if result.rc != 0:
            raise OSError(result.stderr)

        self.__rollback.append(f"rm -fr '{path}'")

    def read(self, path: str) -> str:
        """
        Read remote file and return its contents.

        :param path: File path.
        :type path: str
        :raises OSError: If file can not be read.
        :return: File contents.
        :rtype: str
        """
        result = self.host.exec(['cat', path], log_stdout=False, raise_on_error=False)
        if result.rc != 0:
            raise OSError(result.stderr)

        return result.stdout

    def write(
        self,
        path: str,
        contents: str,
        *,
        mode: str = None,
        user: str = None,
        group: str = None,
        dedent: bool = True,
    ) -> None:
        """
        Write to a remote file.

        :param path: File path.
        :type path: str
        :param contents: File contents to write.
        :type contents: str
        :param mode: Access mode (chmod value), defaults to None
        :type mode: str, optional
        :param user: Owner, defaults to None
        :type user: str, optional
        :param group: Group, defaults to None
        :type group: str, optional
        :param dedent: Automatically dedent and strip file contents, defaults to True
        :type dedent: bool, optional
        :raises OSError: If file can not be written.
        """
        if dedent:
            contents = textwrap.dedent(contents).strip()

        cmd = f'''
        set -x

        if [ -f '{path}' ]; then
            tmp=`mktemp /tmp/mh.fs.rollback.XXXXXXXXX`
            mv --force '{path}' "$tmp"
        fi

        cat >> '{path}'
        {self.__gen_chattrs(path, mode=mode, user=user, group=group)}
        echo $tmp
        '''

        result = self.host.exec(cmd, stdin=contents, log_stdout=False, raise_on_error=False)
        if result.rc != 0:
            raise OSError(result.stderr)

        tmpfile = result.stdout.strip()
        if tmpfile:
            self.__rollback.append(f"mv --force '{tmpfile}' '{path}'")
        else:
            self.__rollback.append(f"rm -fr '{path}'")

    def download(self, remote_path: str, local_path: str) -> None:
        """
        Download file from remote host to local machine.

        :param remote_path: Remote path.
        :type remote_path: str
        :param local_path: Local path.
        :type local_path: str
        """
        result = self.host.exec(['base64', remote_path])
        with open(local_path, 'wb') as f:
            f.write(base64.b64decode(result.stdout))

    def download_files(self, paths: list[str], local_path: str) -> None:
        """
        Download multiple files from remote host. The files are stored in single
        gzipped tarball on the local machine. The remote file path may contain
        glob pattern.

        :param paths: List of remote file paths. May contain glob pattern.
        :type paths: list[str]
        :param local_path: Path to the gzipped tarball destination file on local machine.
        :type local_path: str
        """
        result = self.host.exec(f'''
            tmp=`mktemp /tmp/mh.fs.download_files.XXXXXXXXX`
            tar -czvf "$tmp" {' '.join([f'$(compgen -G "{path}")' for path in paths])} &> /dev/null
            base64 "$tmp"
            rm -f "$tmp" &> /dev/null
        ''')

        with open(local_path, 'wb') as f:
            f.write(base64.b64decode(result.stdout))

    def __gen_chattrs(self, path: str, *, mode: str = None, user: str = None, group: str = None) -> str:
        cmds = []
        if mode is not None:
            cmds.append(f"chmod '{mode}' '{path}'")

        if user is not None:
            cmds.append(f"chown '{user}' '{path}'")

        if group is not None:
            cmds.append(f"chgrp '{group}' '{path}'")

        return ' && '.join(cmds)
