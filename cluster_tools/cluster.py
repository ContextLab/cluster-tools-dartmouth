import getpass
import os
from io import StringIO
from pathlib import Path
from typing import (
    BinaryIO,
    Optional,
    Union,
    TextIO,
    Dict,
    Sequence
)

import spur
import spurplus


PathLike = Union[str, Path]
OneOrMore =


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
            shell: Optional[PathLike] = None,
            cwd: Optional[PathLike] = None,
            env_additions: Optional[Dict[str, str]] = None
    ) -> None:
        """
        TODO: add docstring

        Parameters
        ----------
        hostname
        username
        password
        use_key
        port
        timeout
        retries
        retry_delay
        shell
        cwd
        env_additions
        """
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
            self.username = username
            self.port = port
            env_str = self.shell.run(['printenv']).output.split('\nBASH_FUNC_module()')[0]
            self.environ = dict(map(lambda x: x.split('=', 1), env_str.splitlines()))

        del password

        self.hostname = hostname
        self.env_additions = env_additions or dict()
        self.environ.update(self.env_additions)

        if cwd is None:
            self._cwd = self.environ.get('HOME')
        else:
            self.cwd = cwd

        if shell is None:
            self._SHELL = self.environ.get('SHELL')
        else:
            self.SHELL = shell

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return self.shell.__exit__(*args)

    @property
    def cwd(self) -> str:
        return self._cwd

    @cwd.setter
    def cwd(self, new_cwd: PathLike) -> None:
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
    def SHELL(self) -> str:
        return self._SHELL

    @SHELL.setter
    def SHELL(self, new_shell: PathLike) -> None:
        new_shell = str(new_shell)
        shells_avail = self.shell.run(['cat', '/etc/shells']).output.splitlines()
        if new_shell in shells_avail:
            self._SHELL = new_shell
        else:
            try:
                first_match = [s.split(['/'])[-1] for s in shells_avail].index(new_shell)
                self._SHELL = shells_avail[first_match]
            except IndexError:
                raise AttributeError(f"No executable found for {new_shell}. "
                                     f"Available shells are:\n{', '.join(shells_avail)}")

    def getenv(self, var: str, default: Optional[str] = None) -> str:
        return self.environ.get(var, default=default)

    def putenv(self, var: str, value: str) -> None:
        if var == 'SHELL':
            # updating SHELL env variable also validates & updates self.SHELL
            self.SHELL = value
        self.environ[var] = value

    def unsetenv(self, var: str) -> None:
        self.environ.pop(var)

    def spawn_process(
            self,
            command: Union[str, Sequence[str]],
            stdout: Optional[TextIO] = None,
            stderr: Optional[TextIO] = None,
            stream_encoding='utf-8',
            tty=False
    ) -> 'RemoteProcess':
        # might just be shortcut for self.exec_command(block=True)
        # passing list of strings is equivalent to &&-joining them
        # if stdout/stderr are None, default to just writing to the object

        # format command string
        proc = RemoteProcess()




class RemoteProcess:
    def __init__(
            self,
            command: Union[str, Sequence[str]],
            ssh_shell: Union[spurplus.SshShell, spur.SshShell],
            working_dir: PathLike = None,
            stdout: Optional[Union[TextIO, BinaryIO]] = None,
            stderr: Optional[Union[TextIO, BinaryIO]] = None,
            stream_encoding: str = 'utf-8',
            env_updates: Optional[Dict[str, str]] = None,
            tty: bool = False
    ) -> None:
        self.command = command
        self.ssh_shell = ssh_shell
        self.working_dir = working_dir
        self.stdout = stdout or StringIO()
        self.stderr = stderr or StringIO()
        self.stream_encoding = stream_encoding
        self.env_updates = env_updates
        self.has_tty = tty

        self._proc = None
        self.pid = None

        self.started = False
        self.completed = False

    def run(self):
        self._proc = self.ssh_shell.spawn(command=self.command,
                                          cwd=str(self.working_dir),
                                          env_updates=self.env_updates,
                                          stdout=self.stdout,
                                          stderr=self.stderr,
                                          store_pid=True)
        self.pid = self._proc.pid



# to kill process:
# runner.proc.send_signal('SIGKILL')