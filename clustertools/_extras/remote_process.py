import functools
from typing import Callable, BinaryIO, Dict, Optional, TextIO, Tuple, Union

import spur
import spurplus

from clustertools._extras.exceptions import SshProcessError
from clustertools._extras.multistream_wrapper import MultiStreamWrapper
from clustertools._extras.typing import OneOrMore, PathLike


class RemoteProcess:
    def __init__(
            self,
            command: OneOrMore[str],
            ssh_shell: Union[spurplus.SshShell, spur.SshShell],
            working_dir: Optional[PathLike] = None,
            env_updates: Optional[Dict[str, str]] = None,
            stdout: Optional[Union[OneOrMore[TextIO], OneOrMore[BinaryIO]]] = None,
            stderr: Optional[Union[OneOrMore[TextIO], OneOrMore[BinaryIO]]] = None,
            stream_encoding: Union[str, None] = 'utf-8',
            close_streams: bool = True,
            wait: bool = False,
            allow_error: bool = False,
            use_pty: bool = False,
            callback: Optional[Callable] = None,
            callback_args: Optional[Tuple] = None,
            callback_kwargs: Optional[Dict] = None
    ) -> None:
        # TODO: note that command should be formatted at this point
        self._command = command
        self._ssh_shell = ssh_shell
        self._working_dir = str(working_dir) if working_dir is not None else None
        self._stream_encoding = stream_encoding
        self._env_updates = env_updates
        self._close_streams = close_streams
        self._wait = wait
        self._allow_error = allow_error
        self._use_pty = use_pty
        self._callback = self._setup_user_callback(callback,
                                                   callback_args,
                                                   callback_kwargs)

        self.started = False
        self.completed = False
        self._proc: Optional[spur.ssh.SshProcess] = None
        self.pid: Optional[int] = None
        self.return_code: Optional[int] = None

        # open streams as late as possible
        self.stdout = MultiStreamWrapper(stdout, encoding=stream_encoding)
        self.stderr = MultiStreamWrapper(stderr, encoding=stream_encoding)

    def _process_complete_callback(self):
        if self._close_streams:
            self.stdout.close()
            self.stderr.close()

        # returns immediately when process is complete and sets self._proc._result
        self._proc.wait_for_result()
        self.return_code = self._proc._result.return_code
        self.completed = True
        self._callback()

    def _setup_user_callback(self, cb, cb_args, cb_kwargs):
        cb_args = cb_args or tuple()
        cb_kwargs = cb_kwargs or dict()
        if cb_args or cb_kwargs:
            if cb is None:
                raise ValueError("Callback arguments passed without callable")
            else:
                return functools.partial(cb, *cb_args, **cb_kwargs)
        elif cb:
            return cb
        return lambda: None

    def run(self):
        self._proc = self._ssh_shell.spawn(command=self._command,
                                           cwd=self._working_dir,
                                           update_env=self._env_updates,
                                           stdout=self.stdout,
                                           stderr=self.stderr,
                                           encoding=self._stream_encoding,
                                           allow_error=self._allow_error,
                                           use_pty=self._use_pty,
                                           store_pid=True)
        self.pid = self._proc.pid
        self.started = True
        if self._wait:
            self._proc.wait_for_result()
            self._process_complete_callback()
        else:
            process_observer = AttrObserver(instance=self._proc._channel, attr_name='closed')
            process_observer.register(self._process_complete_callback)

        return self

    def send_signal(self, signal):
        if self.completed:
            raise SshProcessError("Unable to send signal to a completed process")
        elif not self.started:
            raise SshProcessError("The processes has not been started. "
                                  "Use 'RemoteProcess.run()' to start the process.")

        self._proc.send_signal(signal=signal)

    def interrupt(self):
        self.send_signal('SIGINT')

    def kill(self):
        self.send_signal('SIGKILL')

    def terminate(self):
        self.send_signal('SIGTERM')



class AttrObserver:
    def __init__(self, instance, attr_name):
        self.observed_attr = attr_name
        self.observed_instance = instance
        self.observed_class = instance.__class__
        self.instance_observers = {
            instance: {
                'initial_value': getattr(instance, attr_name),
                'current_value': getattr(instance, attr_name)
            }
        }

    def __get__(self, inst, cls=None):
        # TODO: prevent inheritance?
        if inst is None:
            return self
        elif inst in self.instance_observers:
            return self.instance_observers[inst]['current_value']
        else:
            return inst.__dict__[self.observed_attr]

    def __set__(self, inst, val):
        if inst in self.instance_observers:
            self.instance_observers[inst]['current_value'] = val
            self.instance_observers[inst]['callback']()
        else:
            inst.__dict__[self.observed_attr] = val

    def register(self, callback):
        self.instance_observers[self.observed_instance]['callback'] = callback
        # check and see if the attribute exists in the class-level __dict__
        curr_class_attr = getattr(self.observed_class, self.observed_attr, None)
        if isinstance(curr_class_attr, self.__class__):
            # if it does and it's an AttrObserver, add an observer
            # tracking this specific instance to the existing descriptor
            # object (descriptor protocol requires binding to the class
            # object, so there can be only one per attribute name)
            if self.observed_instance in curr_class_attr.instance_observers:
                raise AttributeError("Can't register multiple observers to the "
                                     "same attribute of the same instance")

            curr_class_attr.instance_observers.update(self.instance_observers)
        else:
            # otherwise, register a new data descriptor object on the class
            setattr(self.observed_class, self.observed_attr, self)
