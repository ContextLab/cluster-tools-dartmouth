from pathlib import Path
from typing import Dict, Optional, Sequence, Union

from clustertools.configs.project_config import ProjectConfig
from clustertools.cluster import Cluster
from clustertools.shared.typing import NoneOrMore, OneOrMore, PathLike


class ProjectHandlerMixin:
    @property
    def project_config(self) -> ProjectConfig:
        return self.project.config












################################################################################
################################################################################
################################################################################
################################################################################
# class Project:
#     @classmethod
#     def from_config(cls, config_path):
#         # constructs an instance from data saved in the project config
#         # file in the ~/.clustertools/projects directory
#         pass
#
#     def __init__(
#             self,
#             name: str,
#             root_dir: PathLike = None,
#             #data_dir: PathLike = 'data',
#             #script_dir: PathLike = 'scripts',
#             modules: NoneOrMore = None,
#             env_type: Optional[str] = None,
#             env_name: Optional[str] = None,
#             command_wrapper: Optional[str] = None,
#             batch_name: Optional[str] = None,        # default to username?
#             queue: str = 'largeq',
#             n_nodes: int = 1,
#             ppn: int = 1,
#             wall_time: str = '1:00:00',
#             notify_on: Optional[str] = None,         # TODO: find out default value
#             notify_at: Optional[str] = None          # TODO: find out default value
#     ):
#         # ADD DOCSTRING
#         # project structure setup
#         self.remote_dir = Path(remote_root)
#         self.data_dir = self.remote_dir.joinpath(data_dir)
#         self.script_dir = self.remote_dir.joinpath(script_dir)
#
#         # job environment setup
#         if isinstance(modules, str):
#             self.modules = modules.split()
#         elif isinstance(modules, Sequence):
#             self.modules = list(modules)
#         else:
#             # not strictly enforcing types, but should be None here
#             self.modules = modules
#
#         self.env_type = env_type
#         self.env_name = env_name
#         self.command_wrapper = command_wrapper
#
#         # job runtime setup
#         self.batch_name = batch_name
