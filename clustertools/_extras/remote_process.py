from io import StringIO
from typing import BinaryIO, Dict, Optional, TextIO, Union

import spur
import spurplus

from clustertools._extras.typing import OneOrMore, PathLike
from clustertools._extras.multistream_wrapper import MultiStreamWrapper


class RemoteProcess:
    def __init__(
            self,
            command: OneOrMore[str],
            ssh_shell: Union[spurplus.SshShell, spur.SshShell],
            working_dir: PathLike = None,
            env_updates: Optional[Dict[str, str]] = None,
            stdout: Optional[Union[OneOrMore[TextIO], OneOrMore[BinaryIO]]] = None,
            stderr: Optional[Union[OneOrMore[TextIO], OneOrMore[BinaryIO]]] = None,
            stream_encoding: Union[str, None] = 'utf-8',
            auto_close_streams: bool = True,
            tty: bool = False
    ) -> None:
        self.command = command
        self.ssh_shell = ssh_shell
        self.working_dir = working_dir
        self.stdout = MultiStreamWrapper(stdout, file_encoding=stream_encoding)
        self.stderr = MultiStreamWrapper(stderr, file_encoding=stream_encoding)
        self.stream_encoding = stream_encoding
        self.env_updates = env_updates
        self.has_tty = tty

        self.started = False
        self.completed = False
        self._proc = None
        self.pid = None

    def run(self):
        self._proc = self.ssh_shell.spawn(command=self.command,
                                          cwd=str(self.working_dir),
                                          env_updates=self.env_updates,
                                          stdout=self.stdout,
                                          stderr=self.stderr,
                                          store_pid=True)
        self.pid = self._proc.pid