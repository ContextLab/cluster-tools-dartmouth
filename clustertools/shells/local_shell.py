import getpass
import os
import socket
from pathlib import Path
from subprocess import CalledProcessError
from typing import NoReturn, Optional

import spur

from clustertools.mixins import PseudoEnviron, SshShellMixin
from clustertools.shared.helpers import cleanpath
from clustertools.shared.typing import PathLike


# noinspection PyAttributeOutsideInit
class LocalShellMixin:
    # ADD DOCSTRING
    # TODO: implement self.check_output, which spur.LocalShell doesn't
    #  for some reason (should be just subprocess.check_output)

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
            new_cwd = cleanpath(new_cwd)
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
        #  shells to be set, rather than any existing/executable file
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
        return socket.gethostname()

    @hostname.setter
    def hostname(self, new_hostname) -> NoReturn:
        raise AttributeError("'hostname' does not support assignment for local shells")

    @property
    def shell(self) -> spur.LocalShell:
        if self._shell is None:
            self._shell = spur.LocalShell()
        return self._shell

    @property
    def username(self) -> str:
        return getpass.getuser()

    @username.setter
    def username(self, new_username) -> NoReturn:
        raise AttributeError("'username' does not support assignment for local shells")

    ##########################################################
    #                 FILE SYSTEM INTERFACE                  #
    ##########################################################

    def check_output(self, command, encoding='utf-8') -> str:
        # ADD DOCSTRING
        # TODO: write me
        pass

