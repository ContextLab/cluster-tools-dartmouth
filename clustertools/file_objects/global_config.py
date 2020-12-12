import shutil
from configparser import ConfigParser
from typing import Optional

from clustertools import CLUSTERTOOLS_CONFIG_DIR, CLUSTERTOOLS_TEMPLATES_DIR
from clustertools.cluster import Cluster
from clustertools.file_objects.base_config import BaseConfig
from clustertools.file_objects.config_update_hooks import GLOBAL_CONFIG_UPDATE_HOOKS
from clustertools.shared.typing import PathLike


class GlobalConfig(BaseConfig):
    # ADD DOCSTRING
    # TODO: define __repr__ and/or __str__ methods, plus _repr_html_
    def __init__(self, cluster: Cluster, remote_path: Optional[PathLike] = None) -> None:
        # ADD DOCSTRING
        global_config_path_local = CLUSTERTOOLS_CONFIG_DIR.joinpath('global_config.ini')
        super().__init__(cluster=cluster,
                         local_path=global_config_path_local,
                         remote_path=remote_path)
        self._attr_update_hooks = GLOBAL_CONFIG_UPDATE_HOOKS

    def _init_local(self):
        if not self.local_path.is_file():
            if not CLUSTERTOOLS_CONFIG_DIR.is_dir():
                CLUSTERTOOLS_CONFIG_DIR.mkdir()
            template_path = CLUSTERTOOLS_TEMPLATES_DIR.joinpath('global_config.ini')
            shutil.copy2(str(template_path), str(self.local_path))
        super()._init_local()

    def _init_remote(self):
        if self._config.login.project_dir == '$HOME':
            self._config.login.project_dir = self._cluster.getenv('HOME', default='$HOME')
        super()._init_remote()

    def create_project_config(self, project_name: str) -> ConfigParser:
        # ADD DOCSTRING
        project_parser = ConfigParser(strict=True)
        project_parser['general'] = self._configparser['project_defaults']
        project_parser['runtime_environment'] = self._configparser['project_defaults.runtime_environment']
        project_parser['PBS_params'] = self._configparser['project_defaults.PBS_params']
        project_parser['notifications'] = self._configparser['project_defaults.notifications']
        project_parser['monitoring'] = self._configparser['project_defaults.monitoring']
        if project_parser.get('general', 'job_basename') == 'INFER':
            project_parser.set('general', 'job_basename', project_name)
        project_config_local_path = CLUSTERTOOLS_CONFIG_DIR.joinpath(project_name, 'project_config.ini')
        with project_config_local_path.open('w') as f:
            project_parser.write(f, space_around_delimiters=True)
        return project_parser
