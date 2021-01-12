from __future__ import annotations

from pathlib import PurePosixPath
from typing import TYPE_CHECKING

from clustertools import CLUSTERTOOLS_CONFIG_DIR
from clustertools.file_objects.configs.config_helpers import (
    ParrotDict,
    PROJECT_CONFIG_UPDATE_HOOKS,
    PROJECT_OBJECT_POST_UPDATE_HOOKS,
    type_to_str
)
from clustertools.file_objects.configs.base_config import BaseConfig

if TYPE_CHECKING:
    from clustertools.file_objects.configs.tracked_attr_config import TrackedAttrConfig
    from clustertools.project.project import Project


class ProjectConfig(BaseConfig):
    # ADD DOCSTRING
    def __init__(self, project: Project):
        # ADD DOCSTRING
        # currently, cluster.connected is guaranteed to be True at this point
        cluster = project._cluster
        local_path = CLUSTERTOOLS_CONFIG_DIR.joinpath(project.name,
                                                      'project_config.ini')
        remote_home = PurePosixPath(cluster.getenv('HOME'))
        remote_path = remote_home.joinpath('.clustertools', project.name,
                                           'project_config.ini')
        # needs to happen before BaseConfig._init_local is called
        self._config_update_hooks = ParrotDict()
        self._object_post_update_hooks = ParrotDict()
        self._object_validate_hooks = ParrotDict()
        for field, hook in PROJECT_CONFIG_UPDATE_HOOKS.items():
            self._config_update_hooks[field] = hook(self)
        for field, hook in PROJECT_OBJECT_POST_UPDATE_HOOKS.items():
            self._object_post_update_hooks[field] = hook(self)
        # also needs to happen in case self._init_local calls self._parse_config
        self._project = project
        super().__init__(cluster=cluster,
                         local_path=local_path,
                         remote_path=remote_path)


    def _init_local(self):
        if not self.local_path.is_file():
            if not self.local_path.parent.is_dir():
                # parents=False, exist_ok=False just as a sanity check
                # that ~/.clustertools exists already
                self.local_path.parent.mkdir(parents=False, exist_ok=False)
            self._configparser = self._cluster.config.create_project_config(self._project.name)
            self._config = super()._parse_config()
        else:
            # runs self._load_configparser() and self._parse_config() to
            # set self._configparser and self._config
            super()._init_local()