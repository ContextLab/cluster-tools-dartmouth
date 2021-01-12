from __future__ import annotations

import functools
from threading import Thread
from typing import Any, Callable, Dict, Optional, Tuple, TYPE_CHECKING, Union

from clustertools.shared.exceptions import SSHProcessError
from clustertools.shared.multistream_wrapper import MultiStreamWrapper

if TYPE_CHECKING:
    import spur
    import spurplus
    from clustertools.shared.typing import (MswStderrDest,
                                            MswStdoutDest,
                                            NoneOrMore,
                                            OneOrMore,
                                            PathLike)


# TODO: ensure that all_error=False raises exception in main thread when wait=False
# TODO?: change allow_error={True,False} to on_error={'raise','warn','allow'/'ignore'/'suppress'}
class RemoteProcess:
    # ADD DOCSTRING
    # TODO: this class could use some refactoring...

    @staticmethod
    def _setup_user_callback(
            cb: Optional[Callable[..., Any]],
            cb_args: Optional[Tuple],
            cb_kwargs: Optional[Dict[str, Any]]
    ) -> Callable[[], Any]:
        if cb_args or cb_kwargs:
            if cb is None:
                raise ValueError("Callback arguments passed without callable")
            cb_args = cb_args or tuple()
            cb_kwargs = cb_kwargs or dict()
            return functools.partial(cb, *cb_args, **cb_kwargs)
        elif cb:
            return cb
        else:
            def _placeholder(): pass
            return _placeholder

    def __init__(
            self,
            command: OneOrMore[str],
            ssh_shell: Union[spurplus.SshShell, spur.LocalShell],
            working_dir: Optional[PathLike] = None,
            env_updates: Optional[Dict[str, str]] = None,
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
    ) -> None:
        # ADD DOCSTRING
        #  also note that command should be pre-formatted at this point
        self._command = command
        self._ssh_shell = ssh_shell
        self._working_dir = str(working_dir) if working_dir is not None else None
        self._stream_encoding = stream_encoding
        self._env_updates = env_updates
        self._close_streams = close_streams
        self._wait = wait
        self._allow_error = allow_error
        self._use_pty = use_pty
        self._callback = RemoteProcess._setup_user_callback(callback,
                                                            callback_args,
                                                            callback_kwargs)
        # attributes set later
        self.started = False
        self.completed = False
        self._proc: Optional[spur.ssh.SshProcess] = None
        self.pid: Optional[int] = None
        self._thread: Optional[Thread] = None
        self.return_code: Optional[int] = None
        self.callback_result: Any = None
        # open streams as late as possible
        self.stdout = MultiStreamWrapper(stdout, encoding=stream_encoding)
        self.stderr = MultiStreamWrapper(stderr, encoding=stream_encoding)

    def _process_complete_callback(self) -> None:
        # returns once process is complete and sets self._proc._result
        self._proc.wait_for_result()
        try:
            if self._close_streams:
                self.stdout.close()
                self.stderr.close()
        finally:
            self.completed = True
            self.return_code = self._proc._result.return_code
            if self.return_code == 0:
                # only run callback if no errors raised
                self.callback_result = self._callback()
            elif not self._allow_error:
                raise self._proc._result.to_error()

    def run(self):
        self._proc = self._ssh_shell.spawn(command=self._command,
                                           cwd=self._working_dir,
                                           update_env=self._env_updates,
                                           stdout=self.stdout,
                                           stderr=self.stderr,
                                           encoding=self._stream_encoding,
                                           allow_error=True,
                                           use_pty=self._use_pty,
                                           store_pid=True)
        self.started = True
        self.pid = self._proc.pid
        if self._wait:
            self._process_complete_callback()
        else:
            self._thread = Thread(target=self._process_complete_callback,
                                  name='SshProcessMonitor',
                                  daemon=True)
            self._thread.start()

        return self

    def run_callback(self, overwrite_result: bool = False) -> Any:
        if not self.started:
            raise SSHProcessError(
                "The processes has not been started. Use 'remote_process.run()' "
                "to start the process."
            )
        elif not self.completed:
            raise SSHProcessError(
                "Can't run callback until the process is completed. You can "
                "signal the process to stop using one of:\n"
                "'remote_process.interrupt()', 'remote_process.terminate()', "
                "'remote_process.kill()'"
            )
        new_result = self._callback()
        if self.callback_result is None or overwrite_result:
            self.callback_result = new_result

        return new_result

    def stdin_write(self, value: str) -> None:
        if self.completed:
            raise SSHProcessError("Unable to send input to a completed process")
        elif not self.started:
            raise SSHProcessError(
                "The processes has not been started. Use 'remote_process.run()' "
                "to start the process."
            )

        self._proc.stdin_write(value=value)

    def send_signal(self, signal: Union[str, int]) -> None:
        if self.completed:
            raise SSHProcessError("Unable to send signal to a completed process")
        elif not self.started:
            raise SSHProcessError(
                "The processes has not been started. Use 'remote_process.run()' "
                "to start the process."
            )

        self._proc.send_signal(signal=signal)

    def hangup(self) -> None:
        self.send_signal('SIGHUP')

    def interrupt(self) -> None:
        self.send_signal('SIGINT')

    def kill(self) -> None:
        self.send_signal('SIGKILL')

    def terminate(self) -> None:
        self.send_signal('SIGTERM')
