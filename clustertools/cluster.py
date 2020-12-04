from pathlib import PosixPath, PurePosixPath
from typing import Optional

from clustertools.shells.base_shell import BaseShell
from clustertools.shared.typing import NoneOrMore, PathLike


class Cluster(BaseShell):
    # ADD DOCSTRING
    def __init__(
            self,
            hostname: str,
            username: Optional[str] = None,
            password: Optional[str] = None,
            remote_root: Optional[PathLike] = None,
            data_dir: PathLike = 'data',
            script_dir: PathLike = 'scripts',
            modules: NoneOrMore[str] = None,
            env_type: Optional[str] = None,
            env_name: Optional[str] = None,
            command_wrapper: Optional[str] = None,
            batch_name: Optional[str] = None,        # default to username?
            queue: str = 'largeq',
            n_nodes: int = 1,
            ppn: int = 1,
            wall_time: str = '1:00:00',
            notify_on: Optional[str] = None,  # TODO: find out default value
            notify_at: Optional[str] = None,  # TODO: find out default value
            **ssh_shell_kwargs
    ) -> None:
        # ADD DOCSTRING
        pass

    def _auto_detect_notebook(self):







        # init SSH connection
        # super().__init__(hostname=hostname, username=username, password=password, **ssh_shell_kwargs)

    #     # project structure setup
    #     self._remote_root = None
    #     self._data_subdir = PurePosixPath(data_dir)
    #     self._script_subdir = PurePosixPath(script_dir)
    #     if remote_root is not None:
    #         self.remote_root = PurePosixPath(remote_root)
    #         self.data_dir = self.remote_root.joinpath(self._data_subdir)
    #         self.script_dir = self.remote_root.joinpath(self._script_subdir)
    #         self.data_dir.mkdir(parents=True, exist_ok=True)
    #         self.script_dir.mkdir(parents=True, exist_ok=True)
    #     else:
    #         self.remote_root = None
    #         self.data_dir = None
    #         self.script_dir = None
    #
    # @property
    # def remote_root(self):
    #     return self._remote_root
    #
    # @remote_root.setter
    # def remote_root(self, new_root: PathLike):
    #     if not isinstance(new_root, (str, PosixPath, PurePosixPath)):
    #         raise AttributeError("Must be a str or POSIX-compatible Path object")
    #
    #     new_root = PurePosixPath(new_root)
    #     if not new_root.is_absolute():
    #         raise AttributeError("'remote_root' must be an absolute path")
    #
    #
    #
    #
    #














    ##########################################################
    #                     JOB SUBMISSION                     #
    ##########################################################
    def submit(self, **kwargs):
        pass

    ##########################################################
    #                     JOB MONITORING                     #
    ##########################################################
    def monitor(self):
        pass

    ##########################################################
    #                 JOB OUTPUT COLLECTION                  #
    ##########################################################
