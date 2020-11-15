import getpass
import os
import warnings
from pathlib import Path
from typing import Callable, Optional, Union, Tuple, Dict

import spur
import spurplus
from paramiko import SFTPAttributes

from clustertools._extras.remote_process import RemoteProcess
from clustertools._extras.typing import (MswStderrDest,
                                         MswStdoutDest,
                                         NoneOrMore,
                                         OneOrMore,
                                         PathLike,
                                         Sequence)


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
            self.environ = dict(os.environ)
            self.port: Optional[int] = None
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
            # skip validation if defaulting to $HOME
            self._cwd = Path(self.environ.get('HOME'))
        else:
            # otherwise, run setter
            self.cwd = cwd

        if executable is None:
            # skip validation if defaulting to $SHELL
            self._executable = self.environ.get('SHELL')
        else:
            # otherwise, run setter
            self.executable = executable

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return self.close()

    @property
    def cwd(self) -> str:
        return str(self._cwd)

    @cwd.setter
    def cwd(self, new_cwd: PathLike) -> None:
        # TODO: add docstring
        new_cwd = Path(new_cwd)
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
                print(f"switched to: '{first_match}'")
                self._executable = first_match

    def close(self) -> None:
        # TODO: add docstring
        return self.shell.close()

    ##########################################################
    #                 ENVIRONMENT MANAGEMENT                 #
    ##########################################################
    # analogues to `os` module's `os.environ` modifier functions ####
    def getenv(self, var: str, default: Optional[str] = None) -> str:
        # TODO: add docstring
        return self.environ.get(var, default=default)

    def putenv(self, var: str, value: str) -> None:
        # TODO: add docstring
        # all environ values are stored and retrieved as strings
        var, value = str(var), str(value)
        if var == 'SHELL':
            # updating $SHELL also validates & updates self.SHELL
            self.executable = value
        self.environ[var] = value

    def unsetenv(self, var: str) -> None:
        self.environ.pop(str(var))

    ##########################################################
    #          FILE SYSTEM NAVIGATION & INTERACTION          #
    ##########################################################
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
        full_path = self.resolve_path(path)
        output = self.shell.run([self.executable, '-c', f'test -f {full_path}'],
                                allow_error=True)
        return not bool(output.return_code)

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

    def read(self, path: PathLike, encoding: Union[str, None] = 'utf-8') -> Union[str, bytes]:
        # TODO: add docstring
        path = self.resolve_path(path)
        if encoding is None:
            return self.shell.read_bytes(remote_path=path)
        else:
            return self.shell.read_text(remote_path=path, encoding=encoding)

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

        return orig_type(self.shell.as_sftp().normalize(path))

    def stat(self, path: PathLike = None) -> SFTPAttributes:
        path = self.resolve_path(path)
        return self.shell.stat(remote_path=path)

    def touch(self, path: PathLike, mode=33188, exist_ok=True):
        # TODO: add docstring.
        #  Functions like Pathlib.touch(). if file exists and exist_ok
        #  is True, calls equiv to os.utime to update atime and mtime
        #  like touch does.  Can't be used to change mode on existing
        #  file; use chmod instead
        # mode 33188, octal equiv: '0o100644'
        path = str(self.resolve_path(path))
        if self.exists(path):
            self.shell.as_sftp()._sftp.utime(path, times=None)
        else:
            self.write(path, content='', encoding='utf-8')
            curr_mode = self.shell.stat(path).st_mode
            if curr_mode != mode:
                try:
                    self.chmod(path, mode)
                except NotImplementedError:
                    warnings.warn('chmod/chown functionality not implemented. '
                                  f'File created with permissions: {curr_mode}')

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
