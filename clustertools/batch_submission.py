from pathlib import Path
from typing import Optional, Sequence

from clustertools.shared.typing import NoneOrMore, OneOrMore, PathLike


class BatchSubmission:
    @classmethod
    def from_config(cls, config_path):
        pass

    def __init__(
            self,
            remote_root: PathLike = None,
            datadir: PathLike = 'data',
            scriptdir: PathLike = 'scripts',
            modules: NoneOrMore = None,
            env_type: Optional[str] = None,
            env_name: Optional[str] = None,
            command_wrapper: Optional[str] = None,
            batch_name: Optional[str] = None,        # default to username?
            queue: str = 'largeq',
            n_nodes: int = 1,
            ppn: int = 1,
            wall_time: str = '1:00:00',
            notify_on: Optional[str] = None,         # TODO: find out default value
            notify_at: Optional[str] = None          # TODO: find out default value
    ):
        # TODO: add docstring
        # project structure setup
        self.remote_dir = Path(remote_root)
        self.datadir = self.remote_dir.joinpath(datadir)
        self.scriptdir = self.remote_dir.joinpath(scriptdir)

        # job environment setup
        if isinstance(modules, str):
            self.modules = modules.split()
        elif isinstance(modules, Sequence):
            self.modules = list(modules)
        else:
            # not strictly enforcing types, but should be None here
            self.modules = modules

        self.env_type = env_type
        self.env_name = env_name
        self.command_wrapper = command_wrapper

        # job runtime setup
        self.batch_name = batch_name
