import getpass
import os
import socket
import warnings
from pathlib import Path, PurePosixPath
from typing import Callable, Optional, Union, Tuple, Dict

import spur
import spurplus
from paramiko import SFTPAttributes

from clustertools.shared.remote_process import RemoteProcess
from clustertools.shared.typing import (MswStderrDest,
                                        MswStdoutDest,
                                        NoneOrMore,
                                        OneOrMore,
                                        PathLike,
                                        Sequence)


class SshShell:
    def __init__(
            self,
            hostname: Optional[str] = None,
            username: Optional[str] = None,
            executable: Optional[PathLike] = None,
            cwd: Optional[PathLike] = None,
            env_additions: Optional[Dict[str, str]] = None,
            connect: bool = True,
            **connection_kwargs
    ) -> None:
        # TODO: add docstring
        # TODO: separate self.environ into class with validations,
        #  session/persistent setting, custom __setitem__/__getitem__, etc.

        self.hostname = hostname or 'localhost'
        self.username = username
        self.port = None
        self.timeout = None
        self.retries = None
        self.retry_delay = None

        if connect:
            self.connect(**connection_kwargs)
            # TODO: a more robust solution for this in case BASH_FUNC_module isn't last
            env_str = self.shell.run(['printenv']).output.split('\nBASH_FUNC_module()')[0]
            self._env_orig = dict(map(lambda x: x.split('=', maxsplit=1), env_str.splitlines()))
        else:
            self.shell = spur.LocalShell()
            self.connected = False
            self._env_orig = dict(os.environ)
            if hostname == 'localhost':
                # user wants to run commands in a local shell
                self.hostname = socket.gethostname()
                self.username = getpass.getuser()
            else:
                # user doesn't want to connect yet, but may have passed
                # connection params to constructor
                self.port = connection_kwargs.get('port')
                self.timeout = connection_kwargs.get('timeout')
                self.retries = connection_kwargs.get('retries')
                self.retry_delay = connection_kwargs.get('retry_delay')

        self._env_additions = env_additions or dict()
        # cwd & executable attrs must be set after _env_orig & _env_additions
        self.cwd = cwd
        self.executable = executable

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return self.close()

    @property
    def cwd(self) -> str:
        return str(self._cwd)

    @cwd.setter
    def cwd(self, new_cwd: Optional[PathLike]) -> None:
        # TODO: add docstring
        if new_cwd is None:
            # can skip validation if defaulting/resetting to $HOME
            # used for convenience internally, but is exposed as a valid option to user
            self._cwd = PurePosixPath(self.environ.get('HOME'))
        else:
            new_cwd = PurePosixPath(new_cwd)
            if not new_cwd.is_absolute():
                raise AttributeError('working directory must be an absolute path')
            try:
                assert self.shell.is_dir(new_cwd)
            except AssertionError as e:
                # new_cwd points to a file
                raise NotADirectoryError(f"{new_cwd}: Not a directory") from e
            except FileNotFoundError as e:
                raise FileNotFoundError(f"{new_cwd}: No such file or directory") from e
            else:
                self._cwd = new_cwd

    @property
    def environ(self) -> Dict:
        # TODO: add docstring
        # TODO: implement cache so operations are only run after calls to
        #  self.putenv/self.unsetenv
        #  also need to support deleting vars that weren't set in same session
        #  and actually *unsetting them*, rather than just returning to the default value
        _environ = self._env_orig.copy()
        _environ.update(self._env_additions)
        return _environ

    @property
    def executable(self) -> str:
        # TODO: add docstring
        return self._executable

    @executable.setter
    def executable(self, new_exe: Optional[PathLike]) -> None:
        # TODO: add docstring
        if new_exe is None:
            # like cwd setter, can skip validation if defaulting/resetting to $SHELL
            self._executable = self.environ.get('SHELL')
        else:
            new_exe = str(new_exe)
            shells_file_lines = self.shell.run(['cat', '/etc/shells']).output.splitlines()
            # file may or may not have comments (does on my Mac, doesn't on Discovery)
            exes_avail = [l for l in shells_file_lines if l.startswith(os.path.sep)]
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
                    print(f"switched to: '{first_match}'")
                    self._executable = first_match

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
        # TODO: add docstring
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
        self.shell = spurplus.connect_with_retries(hostname=hostname,
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

    def disconnect(self) -> None:
        # TODO: add docstring
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
        # TODO: add docstring
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
    #                 ENVIRONMENT MANAGEMENT                 #
    ##########################################################
    # analogues to `os` module's `os.environ` methods, plus some extras
    def getenv(self, key: str, default: Optional[str] = None) -> str:
        # TODO: add docstring
        return self.environ.get(key, default=default)

    def putenv(self, key: str, value: str) -> None:
        # TODO: add docstring
        # all environ values are stored and retrieved as strings
        var, value = str(key), str(value)
        if var == 'SHELL':
            # updating $SHELL also validates & updates self.SHELL
            self.executable = value
        self._env_additions[var] = value

    def unsetenv(self, key: str) -> None:
        # TODO: add docstring
        # TODO: deal with unsetting existing vars
        key = str(key)
        try:
            return self._env_additions.pop(key)
        except KeyError:
            if key in self._env_orig:
                raise NotImplementedError("unsetting environment variables not "
                                          "set by the current SshShell is not "
                                          "yet supported")
            else:
                raise

    def updateenv(self, E, **F):
        # TODO: add docstring
        # analogous to dict.update(), params named so signature matches
        self._env_additions.update(E, **F)

    def resetenv(self):
        # TODO: add docstring
        # resets the environment to state before edits from this session
        self._env_additions = dict()

    ##########################################################
    #          FILE SYSTEM NAVIGATION & INTERACTION          #
    ##########################################################
    # TODO: implement os.walk?

    def cat(self, path: PathLike) -> str:
        # TODO: add docstring
        path = str(self.resolve_path(path))
        return self.shell.check_output(['cat', path])

    def chdir(self, path: PathLike) -> None:
        # TODO: add docstring
        path = self.resolve_path(path)
        # functionally equivalent to setting self.cwd property with checks
        self.cwd = path

    def chmod(self, path: PathLike, mode: int) -> None:
        raise NotImplementedError

    def chown(self, path: PathLike, uid: int, gid: int) -> None:
        raise NotImplementedError

    def exists(self, path: PathLike) -> bool:
        # TODO: add docstring
        path = self.resolve_path(path)
        return self.shell.exists(remote_path=path)

    def is_dir(self, path: PathLike) -> bool:
        # TODO: add docstring
        try:
            return self.shell.is_dir(remote_path=path)
        except FileNotFoundError:
            # spurplus.SshShell.is_dir raises FileNotFoundError if path
            # doesn't exist; pathlib.Path.is_dir returns False. pathlib
            # behavior is more logical
            return False

    def is_file(self, path: PathLike) -> bool:
        # TODO: add docstring
        # no straightforward way to do this between spurplus/spur/paramiko,
        # so going for the roundabout way
        path = self.resolve_path(path)
        output = self.shell.run([self.executable, '-c', f'test -f {path}'],
                                allow_error=True)
        return not bool(output.return_code)

    def is_subdir_of(self, subdir: PathLike, parent: PathLike) -> bool:
        # TODO: add docstring
        subdir = PurePosixPath(self.resolve_path(subdir))
        parent = PurePosixPath(self.resolve_path(parent))
        try:
            subdir.relative_to(parent)
            return True
        except ValueError:
            return False

    def listdir(self, path: PathLike = '.') -> None:
        # TODO: add docstring
        path = str(self.resolve_path(path))
        self.shell.as_sftp().listdir(path)

    def mkdir(
            self,
            path: PathLike,
            mode: int = 16877,
            parents: bool = False,
            exist_ok: bool = False
    ) -> None:
        # TODO: add docstring
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
        # TODO: add docstring
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
        # TODO: add docstring.
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
        # TODO: add docstring
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
        # TODO: add docstring
        local_path = Path(os.path.expandvars(Path(local_path).expanduser())).resolve()
        remote_path = self.resolve_path(remote_path)
        self.shell.put(local_path=local_path,
                       remote_path=remote_path,
                       create_directories=create_directories,
                       consistent=consistent)

    def read(self, path: PathLike, encoding: Union[str, None] = 'utf-8') -> Union[str, bytes]:
        # TODO: add docstring
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
        # TODO: add docstring
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


    ##########################################################
    #                SHELL COMMAND EXECUTION                 #
    ##########################################################
    # command-executing methods. Three levels of simplicity vs control,
    # sort of analogous to:
    #   self.check_output()     --> subprocess.check_output()
    #   self.run()              --> subprocess.run()
    #   self.spawn_process()    --> subprocess.Popen()
    def check_output(
            self,
            command: OneOrMore[str],
            options: NoneOrMore[str] = None,
            stderr: bool = False
    ) -> Union[str, Tuple]:
        # TODO: add docstring -- most basic way to run command.
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
        # TODO: add docstring -- simplified interface for running
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
        # TODO: add docstring
        # TODO: note in docstring that '-c' option is added at end automatically
        # might just be base function for self.exec_command(block=True/False).
        # passing list of strings is equivalent to &&-joining them
        # if stdout/stderr are None, default to just writing to the object

        # set defaults and funnel types
        if isinstance(command, str):
            command = [command]
        elif isinstance(command, Sequence):
            command = ' && '.join(command)

        if options is None:
            options = []
        elif isinstance(options, str):
            options = [options]

        if tmp_env is not None:
            _tmp_env = self.environ.copy()
            _tmp_env.update(tmp_env)
            tmp_env = _tmp_env

        # format command string
        full_command = [self.executable]
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
