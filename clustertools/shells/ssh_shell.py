import getpass
import locale
import os
import warnings
from pathlib import PurePosixPath
from typing import Callable, Optional, Union, Tuple, Dict

import spurplus
from paramiko import SFTPAttributes
from spur.results import RunProcessError

from clustertools.mixins import PseudoEnviron
from clustertools.shared.exceptions import SSHConnectionError
from clustertools.shared.remote_process import RemoteProcess
from clustertools.shared.typing import (MswStderrDest,
                                        MswStdoutDest,
                                        NoneOrMore,
                                        OneOrMore,
                                        PathLike,
                                        Sequence)


# noinspection PyAttributeOutsideInit,PyUnresolvedReferences
class SshShellMixin:
    # ADD DOCSTRING
    # TODO: implement recursive option for get/put that uses
    #  spur.SshShell.upload/download method

    @property
    def cwd(self) -> PurePosixPath:
        if not self.connected:
            raise SSHConnectionError("SSH connection must be open to access remote file system")
        return self._cwd

    @cwd.setter
    def cwd(self, new_cwd: Optional[PathLike]) -> None:
        if not self.connected:
            # can't validate if no connected (will be done on connecting)
            self._cwd = PurePosixPath(new_cwd)
        elif new_cwd is None:
            # internal shortcut to skip validation when
            # defaulting/resetting cwd to $HOME
            self._cwd = PurePosixPath(self.environ.get('HOME'))
        else:
            new_cwd = PurePosixPath(new_cwd)
            if not new_cwd.is_absolute():
                raise AttributeError('Working directory must be an absolute path.')
            try:
                assert self.shell.is_dir(new_cwd)
            except AssertionError as e:
                # new_cwd points to a file
                raise NotADirectoryError(f"{new_cwd}: Not a directory") from e
            except FileNotFoundError as e:
                # new_cwd doesn't exist
                raise FileNotFoundError(f"{new_cwd}: No such file or directory") from e
            else:
                self._cwd = new_cwd

    @property
    def environ(self) -> PseudoEnviron:
        if not self.connected:
            raise SSHConnectionError("SSH connection must be open to read remote environment")
        return self._environ

    @property
    def executable(self) -> str:
        # ADD DOCSTRING
        if not self.connected:
            raise SSHConnectionError("SSH connection must be open to determine remote shell")
        return self._executable

    @executable.setter
    def executable(self, new_exe: Optional[PathLike]) -> None:
        # TODO: checking /etc/shells MIGHT be less efficient than
        #  creating/running a RemoteProcess (which has to be done so
        #  full $PATH is set) but would enforce only allowing actual
        #  shells to be set, rather than any executable file
        if not self.connected:
            # can't validate new_exe if not connected (will be done on connecting)
            self._executable = str(new_exe)
        elif new_exe is None:
            # internal shortcut to skip validation when
            # defaulting/resetting executable to $SHELL
            self._executable = self.environ.get('SHELL')
        else:
            new_exe = str(new_exe)
            try:
                # if an executable's name (e.g., "bash") is passed
                # rather than its full path and multiple options exist
                # (e.g., /bin/bash vs /usr/bin/bash), uses first one
                # found in $PATH the same way calling name from shell would
                full_exe_path = self.check_output(['command', -'v', new_exe]).strip()
            except RunProcessError as e:
                raise ValueError(f"No remote executable matching '{new_exe}' "
                                 f"found in $PATH") from e
            else:
                self._executable = full_exe_path

    @property
    def hostname(self) -> str:
        return self._hostname

    @hostname.setter
    def hostname(self, new_hostname: str):
        if self.connected:
            raise AttributeError("Can't update hostname while connection is open")
        self._hostname = new_hostname

    @property
    def shell(self) -> spurplus.SshShell:
        if not self.connected:
            raise SSHConnectionError("SSH connection must be open to access remote shell")
        return self._shell

    @property
    def username(self) -> str:
        return self._username

    @username.setter
    def username(self, new_username: str):
        if self.connected:
            raise AttributeError("Can't update username while connection is open")
        self._username = new_username

    ##########################################################
    #                 FILE SYSTEM INTERFACE                  #
    ##########################################################



    ##########################################################
    #                 CONNECTION MANAGEMENT                  #
    ##########################################################
    def connect(
            self,
            hostname: Optional[str] = None,
            username: Optional[str] = None,
            password: Optional[str] = None,
            use_key: bool = False,
            port: int = 22,
            timeout: int = 60,
            retries: int = 0,
            retry_delay: int = 1
    ) -> None:
        # ADD DOCSTRING
        # TODO: deal with prompting for required fields if not provided
        if self.connected:
            raise ConnectionError('already connected to a remote host. use '
                                  '`SshShell.disconnect` to disconnect from the '
                                  'current host before connecting to a new one, '
                                  'or `SshShell.reconnect` to reset the connection '
                                  'to the current host')

        # for each param, priority is passed value > object attr (> default value)
        hostname = hostname or self.hostname
        username = username or self.username
        port = port or self.port or 22
        timeout = timeout or self.timeout or 60
        retries = retries or self.retries or 0
        retry_delay = retry_delay or self.retry_delay or 1

        if password is None and not use_key:
            password = getpass.getpass('Password: ')
        self._shell = spurplus.connect_with_retries(hostname=hostname,
                                                    username=username,
                                                    password=password,
                                                    use_key=use_key,
                                                    look_for_private_keys=(not use_key),
                                                    port=port,
                                                    connect_timeout=timeout,
                                                    retries=retries,
                                                    retry_period=retry_delay)
        # only update attrs if connection is successful
        self.port = port
        self.timeout = timeout
        self.retries = retries
        self.retry_delay = retry_delay
        self.connected = True

        # TODO: this may HAVE to be self.run so that correct files are
        #  sourced, but also can't be if certain expected fields aren't
        #  set yet

        # TODO: a more robust solution for this in case BASH_FUNC_module isn't last
        initial_env = self.shell.run(['printenv']).output.split('\nBASH_FUNC_module()')[0]
        initial_env = dict(map(lambda x: x.split('=', maxsplit=1), initial_env.splitlines()))
        self._environ = PseudoEnviron(initial_env=initial_env, custom_vars=self._env_additions)

    def disconnect(self) -> None:
        # ADD DOCSTRING
        if not self.connected:
            raise ConnectionError('not currently connected to a remote host')

        self.shell.close()
        self.connected = False
        self.port = self.timeout = self.retries = self.retry_delay = None


    def reconnect(
            self,
            password: Optional[str] = None,
            use_key: bool = False,
            port: Optional[int] = None,
            timeout: Optional[int] = None,
            retries: Optional[int] = None,
            retry_delay: Optional[int] = None,
            reset_env: bool = False,
            reset_cwd: bool = False,
            reset_executable: bool = False
    ) -> None:
        # ADD DOCSTRING
        # port, timeout, retries, retry_delay default to values for current connection
        connect_params = {
            'hostname': self.hostname,
            'username': self.username,
            'password': password,
            'use_key': use_key,
            'port': port or self.port,
            'timeout': timeout or self.timeout,
            'retries': retries or self.retries,
            'retry_delay': retry_delay or self.retry_delay
        }
        if reset_env:
            self.resetenv()

        self.disconnect()
        self.connect(**connect_params)
        if reset_cwd:
            self.cwd = None
        if reset_executable:
            self.executable = None

        self.disconnect()
        self.connect()

    ##########################################################
    #          FILE SYSTEM NAVIGATION & INTERACTION          #
    ##########################################################
    # TODO: implement os.walk?

    def cat(self, path: PathLike) -> str:
        # ADD DOCSTRING
        path = str(self.resolve_path(path))
        return self.shell.check_output(['cat', path])

    def chdir(self, path: PathLike) -> None:
        # ADD DOCSTRING
        path = self.resolve_path(path)
        # functionally equivalent to setting self.cwd property with checks
        self.cwd = path

    def chmod(self, path: PathLike, mode: int) -> None:
        raise NotImplementedError

    def chown(self, path: PathLike, uid: int, gid: int) -> None:
        raise NotImplementedError

    def exists(self, path: PathLike) -> bool:
        # ADD DOCSTRING
        path = self.resolve_path(path)
        return self.shell.exists(remote_path=path)

    def is_dir(self, path: PathLike) -> bool:
        # ADD DOCSTRING
        try:
            return self.shell.is_dir(remote_path=path)
        except FileNotFoundError:
            # spurplus.SshShell.is_dir raises FileNotFoundError if path
            # doesn't exist; pathlib.Path.is_dir returns False. pathlib
            # behavior is more logical
            return False

    def is_file(self, path: PathLike) -> bool:
        # ADD DOCSTRING
        # no Pythonic way to do this between spurplus/spur/paramiko,
        # so going for the roundabout bash way
        path = self.resolve_path(path)
        output = self.shell.run([self.executable, '-c', f'test -f {path}'],
                                allow_error=True)
        return not bool(output.return_code)

    def is_subdir_of(self, subdir: PathLike, parent: PathLike) -> bool:
        # ADD DOCSTRING
        subdir = PurePosixPath(self.resolve_path(subdir))
        parent = PurePosixPath(self.resolve_path(parent))
        try:
            subdir.relative_to(parent)
            return True
        except ValueError:
            return False

    def listdir(self, path: PathLike = '.') -> None:
        # ADD DOCSTRING
        path = str(self.resolve_path(path))
        self.shell.as_sftp().listdir(path)

    def mkdir(
            self,
            path: PathLike,
            mode: int = 16877,
            parents: bool = False,
            exist_ok: bool = False
    ) -> None:
        # ADD DOCSTRING
        # mode 16877, octal equiv: '0o40755' (user has full rights, all
        # others can read/traverse)
        self.shell.mkdir(remote_path=path,
                         mode=mode,
                         parents=parents,
                         exist_ok=exist_ok)

    def remove(self, path: PathLike, recursive: bool = False) -> None:
        path = self.resolve_path(path)
        self.shell.remove(remote_path=path, recursive=recursive)

    def resolve_path(self, path: PathLike) -> PathLike:
        # ADD DOCSTRING
        # os.path.expanduser
        orig_type = type(path)
        path = str(path)
        if path == '~' or path.startswith('~/'):
            path = path.replace('~', '$HOME', 1)

        # make path relative to cwd
        if not path.startswith(('/', '$')):
            path = os.path.join(self.cwd, path)

        # os.path.expandvars
        if '$' in path:
            parts = path.split('/')
            for ix, p in enumerate(parts):
                if p.startswith('$'):
                    parts[ix] = self.getenv(p.replace('$', '', 1), default=p)

            # not using os.path.join actually makes dealing with scenario
            # where ~ or env var ($SOMEVAR/etc/etc) comes first easier
            path = '/'.join(*parts)
            path = path.replace('//', '/')

        return orig_type(self.shell.as_sftp()._sftp.normalize(path))

    def stat(self, path: PathLike = None) -> SFTPAttributes:
        path = self.resolve_path(path)
        return self.shell.stat(remote_path=path)

    def touch(self, path: PathLike, mode: int = 33188, exist_ok: bool = True):
        # ADD DOCSTRING.
        #  Functions like Pathlib.touch(). if file exists and exist_ok
        #  is True, calls equiv to os.utime to update atime and mtime
        #  like touch does.  Can't be used to change mode on existing
        #  file; use chmod instead
        # mode 33188, octal equiv: '0o100644'
        path = str(self.resolve_path(path))
        if self.exists(path):
            if exist_ok:
                self.shell.as_sftp()._sftp.utime(path, times=None)
            else:
                raise FileExistsError(f"")
        else:
            self.write(path, content='', encoding='utf-8')
            curr_mode = self.shell.stat(path).st_mode
            if curr_mode != mode:
                try:
                    self.chmod(path, mode)
                except NotImplementedError:
                    warnings.warn("chmod/chown functionality not implemented. "
                                  f"File created with permissions: {curr_mode}")

    ##########################################################
    #                 FILE TRANSFER & ACCESS                 #
    ##########################################################
    def get(
            self,
            remote_path: PathLike,
            local_path: PathLike,
            create_directories: bool = True,
            consistent: bool = True
    ) -> None:
        # ADD DOCSTRING
        remote_path = self.resolve_path(remote_path)
        # I don't understand why they STILL haven't implemented expandvars for pathlib...
        local_path = Path(os.path.expandvars(Path(local_path).expanduser())).resolve()
        self.shell.get(remote_path=remote_path,
                       local_path=local_path,
                       create_directories=create_directories,
                       consistent=consistent)

    def put(
            self,
            local_path: PathLike = None,
            remote_path: PathLike = None,
            create_directories: bool = True,
            consistent: bool = True
    ) -> None:
        # ADD DOCSTRING
        local_path = Path(os.path.expandvars(Path(local_path).expanduser())).resolve()
        remote_path = self.resolve_path(remote_path)
        self.shell.put(local_path=local_path,
                       remote_path=remote_path,
                       create_directories=create_directories,
                       consistent=consistent)

    def read(self, path: PathLike, encoding: Union[str, None] = 'utf-8') -> Union[str, bytes]:
        # ADD DOCSTRING
        # TODO: fix typing to use @overload
        path = self.resolve_path(path)
        if encoding is None:
            return self.shell.read_bytes(remote_path=path)
        else:
            return self.shell.read_text(remote_path=path, encoding=encoding)

    def write(
            self,
            path: PathLike,
            content: Union[str, bytes],
            encoding: Union[str, None] = 'utf-8',
            create_directories: bool = True,
            consistent: bool = True
    ) -> None:
        # ADD DOCSTRING
        path = self.resolve_path(path)
        if encoding is None:
            self.shell.write_bytes(remote_path=path,
                                   data=content,
                                   create_directories=create_directories,
                                   consistent=consistent)
        else:
            self.shell.write_text(remote_path=path,
                                  text=content,
                                  encoding=encoding,
                                  create_directories=create_directories,
                                      consistent=consistent)