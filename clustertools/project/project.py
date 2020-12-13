from pathlib import Path, PurePosixPath
from typing import Any, Dict, Iterable, List, Literal, NewType, Optional, Union

import numpy as np

from clustertools.cluster import Cluster
from clustertools.file_objects.project_config import ProjectConfig
from clustertools.file_objects.script import ProjectScript
from clustertools.shared.typing import PathLike, WallTimeStr


class Project:
    # ADD DOCSTRING
    # TODO: allow passing scripts as strings? *should* be doable, if
    #  limited in functionality...
    @classmethod
    def load(cls, name: str, cluster: Cluster) -> 'Project':
        ...

    def __init__(
            self,
            name: str,
            cluster: Cluster,
            pre_submit_script: Optional[PathLike] = None,
            job_script: Optional[PathLike] = None,
            collector_script: Optional[PathLike] = None,
            job_params: Optional[Union[List[Dict[str, Any]], Iterable[Iterable], np.ndarray]] = None,

            # CONFIG FIELDS SETTABLE VIA CONSTRUCTOR
            # a little egregious maybe, could wrap all these in
            # **kwargs, but IMO it's helpful to have them visible the
            # method signature & docstring

            job_basename: Optional[str] = None,
            cmd_wrapper: Optional[str] = None,
            modules: Optional[List[str]] = None,
            virtual_env_type: Optional[Literal['conda', 'venv', 'pipenv']] = None,
            virtual_env_name: Optional[str] = None,
            use_cluster_environ: Optional[bool] = None,
            environ_additions: Optional[Dict[str, str]] = None,
            queue: Optional[Literal['default', 'largeq']] = None,
            n_nodes: Optional[int] = None,
            ppn: Optional[int] = None,
            wall_time: Optional[WallTimeStr] = None,
            email_address: Optional[str] = None,
            email_on_submit: Optional[bool] = None,
            email_on_finish: Optional[bool] = None,
            email_on_abort: Optional[bool] = None,
            auto_monitor_jobs: Optional[bool] = None,
            auto_resubmit_jobs: Optional[bool] = None,
            email_on_all_finished: Optional[bool] = None
    ) -> None:
        self._name = name
        self._cluster = cluster
        self.config = ProjectConfig(self)
        if not self._cluster.is_dir(self.data_dir):
            self._cluster.mkdir(self.data_dir, parents=True, exist_ok=True)
        if not self._cluster.is_dir(self.script_dir):
            self._cluster.mkdir(self.script_dir, parents=True, exist_ok=True)
        if pre_submit_script is None:
            self._pre_submit_script = None
        else:
            self.pre_submit_script = pre_submit_script
        if job_script is None:
            self._job_script = None
        else:
            self.job_script = job_script
        if collector_script is None:
            self._collector_script = None
        else:
            self.collector_script = collector_script
        self._job_params = None
        self.jobs = list()
        if job_params is not None:
            self.job_params = job_params

        ...

    # name, root_dir, data_dir, and script_dir are constructed on-the-fly
    # like this so that:
    #  - they can be kept in sync with the relevant fields in self.config
    #  - changing each of these path components involves a slightly
    #    different 'mv'/'rename' command, and dealing with them separately
    #    makes the corresponding code much simpler
    #  - property setup prevents users from changing multiple components
    #    at once (e.g., just setting self.data_dir to something totally
    #    different) which would be difficult to code around defensively
    #  - path components are simpler to store when unloading project,
    #    quicker update on global config field change while project is
    #    unloaded, and easier to reconstruct when reloading later
    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, new_name):
        # TODO: write this. Don't allow rename if any jobs in progress.
        #  Otherwise, change project dirname and all other info that
        #  reflects project name
        ...
        self._name = new_name

    @property
    def root_dir(self) -> PurePosixPath:
        return self._cluster.config.general.project_dir.joinpath(self.name)

    @property
    def data_dir(self) -> PurePosixPath:
        return self.root_dir.joinpath(self.config.general.data_subdir)

    @property
    def script_dir(self) -> PurePosixPath:
        return self.root_dir.joinpath(self.config.general.script_subdir)

    @property
    def pre_submit_script(self) -> ProjectScript:
        return self._pre_submit_script

    @pre_submit_script.setter
    def pre_submit_script(self, script_path: PathLike):
        local_path = Path(script_path).resolve(strict=True)
        file_ext = local_path.suffix
        remote_path = self.script_dir.joinpath(f'pre_submit').with_suffix(file_ext)
        self._pre_submit_script = ProjectScript(cluster=self._cluster,
                                                local_path=local_path,
                                                remote_path=remote_path)

    @property
    def job_script(self) -> ProjectScript:
        return self._job_script

    @job_script.setter
    def job_script(self, script_path: PathLike):
        local_path = Path(script_path).resolve(strict=True)
        file_ext = local_path.suffix
        remote_path = self.script_dir.joinpath(f'runner').with_suffix(file_ext)
        self._job_script = ProjectScript(cluster=self._cluster,
                                         local_path=local_path,
                                         remote_path=remote_path)

    @property
    def collector_script(self) -> ProjectScript:
        return self._collector_script

    @collector_script.setter
    def collector_script(self, script_path: PathLike):
        local_path = Path(script_path).resolve(strict=True)
        file_ext = local_path.suffix
        remote_path = self.script_dir.joinpath(f'collector').with_suffix(file_ext)
        self._collector_script = ProjectScript(cluster=self._cluster,
                                               local_path=local_path,
                                               remote_path=remote_path)

    @property
    def job_params(self) -> Union[List[Dict[str, Any]], List[List, ...], np.ndarray]:
        return self._job_params

    @job_params.setter
    def job_params(self, new_params: Union[List[Dict[str, Any]], List[List, ...], np.ndarray]) -> None:
        old_params = self._job_params
        self._job_params = new_params
        try:
            self.parametrize_jobs()
        except:
            self._job_params = old_params
            raise

    def configure(self):
        pass

# class SimpleDefaultDict(dict):
#     """Similar to collections.defaultdict, but doesn't add missing keys
#     """
#     def __missing__(self, key):
#         return '?'