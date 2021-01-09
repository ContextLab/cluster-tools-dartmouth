from __future__ import annotations

import getpass
import inspect
import os
import socket
from pathlib import Path
from typing import (Callable,
                    cast,
                    Dict,
                    Optional,
                    Union,
                    Tuple,
                    Type,
                    TYPE_CHECKING,
                    Sequence)

import spur

from clustertools.shells.local_shell import LocalShellMixin
from clustertools.shells.ssh_shell import SshShellMixin
from clustertools.shared.remote_process import RemoteProcess

if TYPE_CHECKING:
    from clustertools.shared.typing import (MswStderrDest,
                                            MswStdoutDest,
                                            NoneOrMore,
                                            OneOrMore,
                                            PathLike)


class BaseShell:
    # ADD DOCSTRING
    # TODO: test use as context manager when spawning a process that runs
    #  longer than the context block
    def __new__(cls: Type[BaseShell], *args, **kwargs) -> BaseShell:
        signature = inspect.signature(cls.__init__)
        bound_args = signature.bind_partial(*args, **kwargs)
        bound_args.apply_defaults()
        if bound_args.arguments['hostname'] == 'localhost':
            shell_mixin = LocalShellMixin
            raise NotImplementedError("Configuration for local deployment is "
                                      "not yet fully supported")
        else:
            shell_mixin = SshShellMixin
        bases = (cls, shell_mixin)
        # TODO: could vary the name here based on which mixin is used as
        #  long as it doesn't mess with Cluster inheritance
        instance = super().__new__(type(cls.__name__, bases, dict(cls.__dict__)))
        # typing.cast isn't evaluated at runtime; equivalent to 'return instance'
        return cast(BaseShell, instance)

    def __init__(
            self,
            hostname: Optional[str] = None,
            username: Optional[str] = None,
            password: Optional[str] = None,
            cwd: Optional[PathLike] = None,
            executable: Optional[PathLike] = None,
            env_additions: Optional[Dict[str, str]] = None,
            connect: bool = True,
            **connection_kwargs
    ) -> None:
        # ADD DOCSTRING -- note circular issue: if using an executable
        #  other than /bin/bash, you should either pass it to
        #  constructor or set it before connecting, otherwise some
        #  environment variables may missing or incorrect. When first
        #  connecting, environment variables are read from output of
        #  printenv, which is affected by the executable used to run the
        #  command. So even though $SHELL will be read and used as the
        #  default executable if one is not explicitly before
        #  connecting, other environment variables will reflect having
        #  been read from a bash shell

        self._env_additions = env_additions or dict()
        self._environ = None
        self._cwd = cwd
        self._executable = executable
        self.connected = False
        if hostname == 'localhost':
            self._shell = spur.LocalShell()
            self._hostname = socket.gethostname()
            self._username = getpass.getuser()
            self._port = None
        else:
            self._shell = None
            self._hostname = hostname
            self._username = username
            self._port = connection_kwargs.pop('port', None)
            if connect:
                self.connect(password=password, **connection_kwargs)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.connected:
            self.disconnect()
        return

    ##########################################################
    #                 ENVIRONMENT MANAGEMENT                 #
    ##########################################################
    # analogues to `os` module's environ-modifying methods, plus some
    # extras.
    # unlike os.putenv/os.unsetenv, these DO modify the environ object
    # itself, so they're as safe as calling `os.environ`'s dict methods
    # directly.
    def getenv(self, key: str, default: Optional[str] = None) -> Union[str, None]:
        # ADD DOCSTRING
        return self.environ.get(key, default)

    def putenv(self, key: str, value: str) -> None:
        # ADD DOCSTRING
        self.environ[key] = value

    def unsetenv(self, key: str) -> None:
        # ADD DOCSTRING
        del self.environ[key]

    ##########################################################
    #                 FILE SYSTEM INTERFACE                  #
    ##########################################################
    def _expandvars(self, path: PathLike, pathsep: str = '/') -> PathLike:
        # os.path.expandvars, but uses self.environ.
        # Note: that this doesn't account for an environment variable
        # that references  another environment variable, but neither
        # does os.path.expandvars
        if '$' in str(path):
            path_type = type(path)
            parts = str(path).split(pathsep)
            for ix, p in enumerate(parts):
                if p.startswith('$'):
                    parts[ix] = self.environ.get(p[1:].strip('{}'), p)
            # fix any substitution or joining inconsistencies, restore
            # to input type
            path = path_type(pathsep.join(parts).replace('//', '/'))
        return path

    def _resolve_path_local(
            self,
            path: PathLike,
            cwd: Optional[PathLike] = None,
            strict: bool = False
    ) -> PathLike:
        # cwd defaults to CWD if not provided
        cwd = Path.cwd() if cwd is None else cwd
        path_type = type(path)
        # substitute environment variables
        path = self._expandvars(path=path, pathsep=os.path.sep)
        # expand tilde
        path = os.path.expanduser(path)
        # resolve relative to CWD, replace symlinks, restore to input type
        return path_type(Path(cwd, path).resolve(strict=strict))

    def _resolve_path_remote(
            self,
            path: PathLike,
            cwd: PathLike,
            strict: bool = False
    ) -> PathLike:
        # substitute environment variables
        path = self._expandvars(path=path, pathsep='/')
        # the rest has to be done manually because we can't use any
        # "concrete" pathlib.Path or os.path methods
        path_type = type(path)
        path = str(path)
        # os.path.expanduser (could implement this for other users using
        # pwd module, but probably not worthwhile)
        path = path.replace(f'~{self.username}', self.environ.get('HOME'), 1)
        path = path.replace('~', self.environ.get('HOME'), 1)
        # os.path.realpath (os.path.abspath + resolving symlinks)
        # may be better to use self.shell.as_sftp()._sftp.normalize(path),
        # but ReconnectingSFTP's _sftp attr is only set after calling
        # certain other methods that aren't guaranteed to have been used
        # before this
        if not path.startswith('/'):
            path = os.path.join(cwd, path)
        full_path = os.path.normpath(path)
        # TODO: this is nearly circular with self.exists(). Fix this.
        if strict and not self.exists(full_path):
            # format follows exception raised for pathlib.Path.resolve(strict=True)
            raise FileNotFoundError("[Errno 2] No such file or directory: "
                                    f"'{full_path}'")
        return path_type(full_path)

    def chdir(self, path: PathLike) -> None:
        # ADD DOCSTRING
        # equivalent to self.cwd property's setter with checks
        self.cwd = path

    def getcwd(self) -> str:
        # ADD DOCSTRING
        # convenience method to get stringify self.cwd (like os.getcwd)
        return str(self.cwd)

    ##########################################################
    #                SHELL COMMAND EXECUTION                 #
    ##########################################################
    # command-executing methods. Three levels of simplicity vs control,
    # analogous to:
    #   self.check_output()   -->  subprocess.check_output()
    #   self.run()            -->  subprocess.run()
    #   self.spawn_process()  -->  subprocess.Popen()
    def check_output(
            self,
            command: OneOrMore[str],
            options: NoneOrMore[str] = None,
            stderr: bool = False
    ) -> Union[str, Tuple]:
        # ADD DOCSTRING -- most basic way to run command.
        finished_proc = self.run(command=command, options=options, allow_error=False)
        if stderr:
            return finished_proc.stdout.final, finished_proc.stderr.final
        else:
            return finished_proc.stdout.final

    def run(
            self,
            command: OneOrMore[str],
            options: NoneOrMore[str] = None,
            working_dir: Optional[PathLike] = None,
            tmp_env: Optional[Dict[str, str]] = None,
            allow_error: bool = False
    ) -> RemoteProcess:
        # ADD DOCSTRING -- simplified interface for running
        #  commands. For finer control, use spawn_process. Will always
        #  wait for process to finish & return completed process
        return self.spawn_process(command=command,
                                  options=options,
                                  working_dir=working_dir,
                                  tmp_env=tmp_env,
                                  allow_error=allow_error,
                                  wait=True)

    def spawn_process(
            self,
            command: OneOrMore[str],
            executable: Optional[str] = None,
            options: NoneOrMore[str] = None,
            working_dir: Optional[PathLike] = None,
            tmp_env: Optional[Dict[str, str]] = None,
            stdout: NoneOrMore[MswStdoutDest] = None,
            stderr: NoneOrMore[MswStderrDest] = None,
            stream_encoding: Union[str, None] = 'utf-8',
            close_streams: bool = True,
            wait: bool = False,
            allow_error: bool = False,
            use_pty: bool = False,
            callback: Optional[Callable] = None,
            callback_args: Optional[Tuple] = None,
            callback_kwargs: Optional[Dict] = None
    ) -> RemoteProcess:
        # ADD DOCSTRING -- note that:
        #  - '-c' option is appended automatically
        #  - passing list of strings is equivalent to &&-joining them
        #  - if stdout/stderr are None, defaults to just writing to the object
        # set defaults and funnel types
        if isinstance(command, Sequence):
            command = ' && '.join(command)
        executable = executable or self.executable
        if options is None:
            options = list()
        elif isinstance(options, str):
            options = [options]
        if tmp_env is not None:
            _base_env = self.environ.copy()
            _base_env.update(tmp_env)
            tmp_env = _base_env
        else:
            tmp_env = dict(self.environ)
        # format command string
        full_command = [executable]
        for opt in options:
            full_command.extend(opt.split())
        full_command.append('-c')
        full_command.append(command)
        # create RemoteProcess instance
        proc = RemoteProcess(command=command,
                             ssh_shell=self.shell,
                             working_dir=working_dir,
                             env_updates=tmp_env,
                             stdout=stdout,
                             stderr=stderr,
                             stream_encoding=stream_encoding,
                             close_streams=close_streams,
                             wait=wait,
                             allow_error=allow_error,
                             use_pty=use_pty,
                             callback=callback,
                             callback_args=callback_args,
                             callback_kwargs=callback_kwargs)
        return proc.run()
