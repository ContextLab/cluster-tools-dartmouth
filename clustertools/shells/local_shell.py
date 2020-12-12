import os
import shutil
from pathlib import Path
from subprocess import CalledProcessError
from typing import List, NoReturn, Optional, Union

import spur

from clustertools.shared.environ import PseudoEnviron
from clustertools.shells.ssh_shell import SshShellMixin
from clustertools.shared.typing import PathLike


## noinspection PyAttributeOutsideInit, PyUnresolvedReferences
class LocalShellMixin:
    # ADD DOCSTRING
    def __getattr__(self, item):
        if hasattr(SshShellMixin, item):
            message = f"'{item}' is not supported for local shells"
        else:
            message = f"'{self.__class__.__name__}' has no attribute '{item}'"
        raise AttributeError(message)

    @property
    def cwd(self) -> Path:
        return self._cwd

    @cwd.setter
    def cwd(self, new_cwd: PathLike):
        try:
            new_cwd = Path(new_cwd)
        except TypeError as e:
            if new_cwd is None:
                # internal shortcut to skip validation when
                # defaulting/resetting executable to $HOME
                self._cwd = Path(self.environ.get('HOME'))
            else:
                raise AttributeError("'cwd' must be a 'str' or "
                                     "'pathlib.Path'-like object") from e
        else:
            new_cwd = self.resolve_path(new_cwd)
            if new_cwd.is_dir():
                self._cwd = new_cwd
            elif new_cwd.is_file():
                raise NotADirectoryError(f"{new_cwd}: Not a directory")
            else:
                raise FileNotFoundError(f"{new_cwd}: No such file or directory")

    @property
    def environ(self) -> PseudoEnviron:
        if self._environ is None:
            self._environ = PseudoEnviron(initial_env=dict(os.environ),
                                          custom_vars=self._env_additions)
        return self._environ

    @property
    def executable(self) -> str:
        return self._executable

    @executable.setter
    def executable(self, new_exe: Optional[PathLike]):
        # TODO: checking /etc/shells MIGHT be less efficient than
        #  creating/running a RemoteProcess (which has to be done so
        #  full $PATH is set) but would enforce only allowing actual
        #  shells, rather than any existing/executable file
        if new_exe is None:
            # internal shortcut to skip validation when
            # defaulting/resetting executable to $SHELL
            self._executable = self.environ.get('SHELL')
        else:
            new_exe = str(new_exe)
            # if an executable's name (e.g., "bash") is passed
            # rather than its full path and multiple options exist
            # (e.g., /bin/bash vs /usr/bin/bash), uses first one found
            # in $PATH the same way calling name from shell would
            try:
                full_exe_path = self.check_output(['command', '-v', str(new_exe)]).strip()
            except CalledProcessError as e:
                raise ValueError(f"No local executable matching '{new_exe}' "
                                 f"found in $PATH") from e

    @property
    def hostname(self) -> str:
        return self._hostname

    @hostname.setter
    def hostname(self, new_hostname) -> NoReturn:
        raise AttributeError("'hostname' does not support assignment for local shells")

    @property
    def port(self) -> int:
        return self._port

    @port.setter
    def port(self, new_port) -> NoReturn:
        raise AttributeError("'port' does not support assignment for local shells")

    @property
    def shell(self) -> spur.LocalShell:
        return self._shell

    @property
    def username(self) -> str:
        return self._username

    @username.setter
    def username(self, new_username) -> NoReturn:
        raise AttributeError("'username' does not support assignment for local shells")

    ##########################################################
    #                 FILE SYSTEM INTERFACE                  #
    ##########################################################
    def chmod(self, path: PathLike, mode: int) -> None:
        # ADD DOCSTRING
        return Path(path).chmod(mode=mode)

    def chown(
            self,
            path: PathLike,
            user: Union[str, int, None] = None,
            group: Union[str, int, None] = None
    ) -> None:
        # ADD DOCSTRING
        return shutil.chown(path=str(path), user=user, group=group)

    def exists(self, path: PathLike) -> bool:
        # ADD DOCSTRING
        return self.resolve_path(Path(path), strict=False).exists()

    def is_dir(self, path: PathLike) -> bool:
        # ADD DOCSTRING
        # spurplus.SshShell.is_dir raises FileNotFoundError if path
        # doesn't exist; pathlib.Path.is_dir returns False. pathlib
        # behavior is more logical, so going with that
        return self.resolve_path(Path(path), strict=False).is_dir()

    def is_file(self, path: PathLike) -> bool:
        # ADD DOCSTRING
        return self.resolve_path(Path(path), strict=False).is_file()

    def listdir(self, path: PathLike = '.') -> List[str]:
        # ADD DOCSTRING
        return os.listdir(self.resolve_path(path, strict=False))

    def mkdir(
            self,
            path: PathLike,
            mode: int = 16877,
            parents: bool = False,
            exist_ok: bool = False
    ) -> None:
        # ADD DOCSTRING
        path = self.resolve_path(Path(path), strict=False)
        return path.mkdir(mode=mode, parents=parents, exist_ok=exist_ok)

    def read_bytes(self, path: PathLike) -> bytes:
        # ADD DOCSTRING
        return self.resolve_path(Path(path), strict=True).read_bytes()

    def read_text(self, path: PathLike, encoding: str = 'utf-8') -> str:
        # ADD DOCSTRING
        # TODO: support "errors" kwarg?
        path = self.resolve_path(Path(path), strict=True)
        return path.read_text(encoding=encoding, errors=None)

    def remove(self, path: PathLike, recursive: bool = False) -> None:
        # ADD DOCSTRING
        path = self.resolve_path(Path(path), strict=True)
        if path.is_dir():
            if recursive:
                # uses defaults for ignore_errors and onerror
                return shutil.rmtree(path=path, ignore_errors=False, onerror=None)
            else:
                # will throw OSError if directory is not empty
                path.rmdir()
        else:
            path.unlink(missing_ok=False)

    def resolve_path(self, path: PathLike, strict: bool = False) -> PathLike:
        return self._resolve_path_local(path=path, cwd=self.cwd, strict=strict)

    def stat(self, path: PathLike = None) -> os.stat_result:
        # ADD DOCSTRING
        return self.resolve_path(Path(path), strict=True).stat()

    def touch(self, path: PathLike, mode: int = 33188, exist_ok: bool = True):
        # ADD DOCSTRING
        path = self.resolve_path(Path(path), strict=False)
        return path.touch(mode=mode, exist_ok=exist_ok)

    def write_bytes(self, path: PathLike, data: bytes) -> None:
        # ADD DOCSTRING
        self.resolve_path(Path(path), strict=False).write_bytes(data=data)
        return None

    def write_text(
            self,
            path: PathLike,
            data: str,
            encoding: str = 'utf-8',
    ) -> None:
        # ADD DOCSTRING
        # TODO: support "errors" kwarg?
        path = self.resolve_path(Path(path), strict=False)
        path.write_text(data=data, encoding=encoding, errors=None)
        return None
