from __future__ import annotations

import shutil
from configparser import ConfigParser
from typing import Optional, TYPE_CHECKING

from clustertools import CLUSTERTOOLS_CONFIG_DIR, CLUSTERTOOLS_TEMPLATES_DIR
from clustertools.file_objects.configs.base_config import BaseConfig
from clustertools.file_objects.configs.config_helpers import (
    GLOBAL_CONFIG_UPDATE_HOOKS,
    GLOBAL_OBJECT_POST_UPDATE_HOOKS,
    ParrotDict
)

if TYPE_CHECKING:
    from clustertools.cluster import Cluster
    from clustertools.shared.typing import PathLike


class GlobalConfig(BaseConfig):
    # ADD DOCSTRING
    # TODO: define __repr__ and/or __str__ methods, plus _repr_html_
    def __init__(self, cluster: Cluster, remote_path: Optional[PathLike] = None) -> None:
        # ADD DOCSTRING
        global_config_path_local = CLUSTERTOOLS_CONFIG_DIR.joinpath('global_config.ini')
        # needs to happen before BaseConfig._init_local is called
        self._config_update_hooks = ParrotDict()
        self._object_post_update_hooks = ParrotDict()
        self._object_validate_hooks = ParrotDict()
        for field, hook in GLOBAL_CONFIG_UPDATE_HOOKS.items():
            self._config_update_hooks[field] = hook(self)
        for field, hook in GLOBAL_OBJECT_POST_UPDATE_HOOKS.items():
            self._object_post_update_hooks[field] = hook(self)
        super().__init__(cluster=cluster,
                         local_path=global_config_path_local,
                         remote_path=remote_path)

    def _init_local(self):
        # need to make sure the config exists before
        # BaseConfig._init_local parses it
        if not self.local_path.is_file():
            if not CLUSTERTOOLS_CONFIG_DIR.is_dir():
                CLUSTERTOOLS_CONFIG_DIR.mkdir()
            template_path = CLUSTERTOOLS_TEMPLATES_DIR.joinpath('global_config.ini')
            shutil.copy2(str(template_path), str(self.local_path))
        super()._init_local()

    def _init_remote(self):
        super()._init_remote()
        if self._config.general.project_dir == '$HOME':
            self._config.general.project_dir = self._cluster.getenv('HOME', default='$HOME')

    def create_project_config(self, project_name: str) -> ConfigParser:
        # ADD DOCSTRING - creates the project_config.ini file and ConfigParser
        #  object for a newly created project
        # TODO: given how the project config is created, the template
        #  file probably doesn't even need to exist
        project_parser = ConfigParser(strict=True)
        project_parser['general'] = self._configparser['project_defaults']
        project_parser['runtime_environment'] = self._configparser['project_defaults.runtime_environment']
        project_parser['pbs_params'] = self._configparser['project_defaults.pbs_params']
        project_parser['notifications'] = self._configparser['project_defaults.notifications']
        project_parser['monitoring'] = self._configparser['project_defaults.monitoring']
        if project_parser.get('general', 'job_basename') == '<DEFAULT>':
            project_parser.set('general', 'job_basename', project_name)
        project_config_local_path = CLUSTERTOOLS_CONFIG_DIR.joinpath(project_name,
                                                                     'project_config.ini')
        with project_config_local_path.open('w') as f:
            project_parser.write(f, space_around_delimiters=True)
        return project_parser
