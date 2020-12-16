from __future__ import annotations

from pathlib import PurePosixPath
from typing import TYPE_CHECKING

from clustertools import CLUSTERTOOLS_CONFIG_DIR
from clustertools.file_objects.config_hooks import (PROJECT_CONFIG_UPDATE_HOOKS,
                                                    write_updated_config)
from clustertools.file_objects.base_config import BaseConfig

if TYPE_CHECKING:
    from clustertools.file_objects.tracked_attr_config import TrackedAttrConfig
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
        # needs to happen before _init_local is called
        self._attr_update_hooks = PROJECT_CONFIG_UPDATE_HOOKS
        self._project = project
        super().__init__(cluster=cluster,
                         local_path=local_path,
                         remote_path=remote_path)

    def _environ_update_hook(self):
        environ_str = BaseConfig._environ_to_str(self._config.environ)
        self._configparser.set('runtime_environment', 'environ', environ_str)
        self.write_config_file()

    def _init_local(self):
        global write_updated_config
        if not self.local_path.is_file():
            if not self.local_path.parent.is_dir():
                # parents=False, exist_ok=False just as a sanity check
                # that ~/.clustertools exists already
                self.local_path.parent.mkdir(parents=False, exist_ok=False)
            # bind hooks to instance
            for field, hook in self._attr_update_hooks.items():
                self._attr_update_hooks[field] = hook(self)
            write_updated_config = write_updated_config(self)
            self._configparser = self._cluster.config.create_project_config(self._project.name)
            self._config = self._parse_config()
        else:
            # runs self._load_configparser() and self._parse_config() to
            # set self._configparser and self._config
            super()._init_local()

    def _modules_update_hook(self):
        modules_str = ', '.join(self._config.project_defaults.runtime_environment.modules)
        self._configparser.set('runtime_environment', 'modules', modules_str)
        self.write_config_file()

    def _parse_config(self) -> TrackedAttrConfig:
        # priority order for project environment variables
        # (highest to lowest):
        #  - vars set after creating Project object but before
        #    submitting jobs
        #  - vars passed to the Project constructor TODO: make this possible
        #  - vars set in project_config.ini (whether by default or from
        #    load of previous state)
        #  - vars set on Cluster object after creation
        #    (if use_global_environ)
        #  - vars passed to Cluster constructor (if use_global_environ)
        # TODO: additional sources to update this with?
        use_global_environ = self._configparser.getboolean('runtime_environment',
                                                            'use_global_environ')
        if use_global_environ:
            _global_env = self._cluster.environ
            custom_global_vars = {
                ev: val
                for ev, val in _global_env.items()
                    if val != _global_env._initial_env.get(ev, None)
            }
            if any(custom_global_vars):
                project_config_env = self._configparser.get('runtime_environment',
                                                            'environ')
                project_config_env = map(lambda x: x.split('='),
                                         project_config_env.strip().splitlines())
                project_config_env = {
                    k.strip(): v.strip() for k, v in project_config_env
                }
                custom_global_vars.update(project_config_env)
                environ_str = BaseConfig._environ_to_str(custom_global_vars)
                self._configparser.set('runtime_environment', 'environ', environ_str)
        return super()._parse_config()
