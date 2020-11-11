import getpass
import os
from io import StringIO
from typing import (
    BinaryIO,
    Optional,
    Union,
    TextIO,
    Dict
)

import spur
import spurplus

from clustertools._extras.typing import OneOrMore, PathLike


class Cluster:
    def __init__(
            self,
            hostname: str,
            username: Optional[str] = None,
            password: Optional[str] = None,
            use_key: bool = False,
            port: int = 22,
            timeout: int = 60,
            retries: int = 0,
            retry_delay: int = 1,
            executable: Optional[PathLike] = None,
            cwd: Optional[PathLike] = None,
            env_additions: Optional[Dict[str, str]] = None
    ) -> None:
        # TODO: add docstring
        # TODO: separate self.environ into class with validations, session/persistent setting, etc.
        # setup connection first for fast failure
        if hostname == 'localhost':
            self.shell = spur.LocalShell()
            self.username = getpass.getuser()
            self.port = None
            self.environ = dict(os.environ)
        else:
            self.shell = spurplus.connect_with_retries(hostname=hostname,
                                                       username=username,
                                                       password=(getpass.getpass('Password: ') if not (use_key or password) else password),
                                                       look_for_private_keys=(not use_key),
                                                       port=port,
                                                       connect_timeout=timeout,
                                                       retries=retries,
                                                       retry_period=retry_delay)
            del password

            self.username = username
            self.port = port
            # TODO: a more robust solution for this in case BASH_FUNC_module isn't last
            env_str = self.shell.run(['printenv']).output.split('\nBASH_FUNC_module()')[0]
            self.environ = dict(map(lambda x: x.split('=', maxsplit=1), env_str.splitlines()))

        self.hostname = hostname
        self.env_additions = env_additions or dict()
        self.environ.update(self.env_additions)

        if cwd is None:
            # bypass validation if using HOME from environment
            self._cwd = self.environ.get('HOME')
        else:
            # otherwise, call setter
            self.cwd = cwd

        if executable is None:
            self._executable = self.environ.get('SHELL')
        else:
            self.executable = executable

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return self.shell.__exit__(*args)

    @property
    def cwd(self) -> str:
        return self._cwd

    @cwd.setter
    def cwd(self, new_cwd: PathLike) -> None:
        # TODO: add docstring
        new_cwd = str(new_cwd)
        if not new_cwd.startswith('/'):
            raise AttributeError('working directory must be an absolute path')
        try:
            assert self.shell.is_dir(new_cwd)
        except (AssertionError, FileNotFoundError) as e:
            if isinstance(e, AssertionError):
                reason = f"Path points to a file"
            else:
                reason = f"Path does not exist"
            raise AttributeError("Can't set working directory to "
                                 f"{new_cwd}. {reason}")
        else:
            self._cwd = new_cwd

    @property
    def executable(self) -> str:
        return self._executable

    @executable.setter
    def executable(self, new_exe: PathLike) -> None:
        # TODO: add docstring
        new_exe = str(new_exe)
        exes_avail = self.shell.run(['cat', '/etc/shells']).output.splitlines()
        if new_exe in exes_avail:
            # full path was passed (e.g., '/bin/bash')
            self._executable = new_exe
        else:
            # shorthand was passed (e.g., 'bash')
            try:
                # get full path of first matching option in /etc/shells
                first_match = next(s for s in exes_avail if s.endswith(new_exe))
            except StopIteration:
                raise AttributeError(f"No executable found for {new_exe}. "
                                     f"Available shells are:\n{', '.join(exes_avail)}")
            else:
                # if shorthand was passed, print full path to confirm
                print(f"switched executable to '{first_match}'")
                self._executable = first_match

    def getenv(self, var: str, default: Optional[str] = None) -> str:
        # TODO: add docstring
        return self.environ.get(var, default=default)

    def putenv(self, var: str, value: str) -> None:
        # TODO: add docstring
        if var == 'SHELL':
            # updating SHELL env variable also validates & updates self.SHELL
            self.executable = value
        self.environ[var] = value

    def unsetenv(self, var: str) -> None:
        self.environ.pop(var)

    def spawn_process(
            self,
            command: OneOrMore[str],
            stdout: Optional[OneOrMore[TextIO]] = None,
            stderr: Optional[OneOrMore[TextIO]] = None,
            stream_encoding='utf-8',
            tty=False
    ) -> 'RemoteProcess':
        # might just be base function for self.exec_command(block=True/False).
        # passing list of strings is equivalent to &&-joining them
        # if stdout/stderr are None, default to just writing to the object

        # format command string
        proc = RemoteProcess()








# to kill process:
# runner.proc.send_signal('SIGKILL')