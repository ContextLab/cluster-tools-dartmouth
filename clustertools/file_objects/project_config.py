from clustertools import CLUSTERTOOLS_CONFIG_DIR
from clustertools.project.project import Project
from clustertools.file_objects.tracked_attr_config import TrackedAttrConfig
from clustertools.file_objects.base_config import BaseConfig


class ProjectConfig(BaseConfig):
    # ADD DOCSTRING
    def __init__(self, project: Project):
        # ADD DOCSTRING
        # currently, cluster.connected is guaranteed to be True at this point
        cluster = project._cluster
        local_path = CLUSTERTOOLS_CONFIG_DIR.joinpath(project.name, 'project_config.ini')
        remote_path = cluster.getenv('HOME').joinpath('.clustertools', project.name, 'project_config.ini')
        super().__init__(cluster=cluster, local_path=local_path, remote_path=remote_path)
        self._project = project

    def _environ_update_hook(self):
        environ_str = BaseConfig._environ_to_str(self._config.environ)
        self._configparser.set('runtime_environment', 'environ', environ_str)
        self.write_config_file()


    def _init_local(self):
        if not self.local_path.is_file():
            if not self.local_path.parent.is_dir():
                # parents=False, exist_ok=False just as a sanity check
                # that ~/.clustertools exists already
                self.local_path.parent.mkdir(parents=False, exist_ok=False)
            self._configparser = self._cluster.config.create_project_config(self._project.name)
            self._config = self._parse_config()
        else:
            # runs self._load_configparser() and self._parse_config() to
            # set self._configparser and self._config
            super()._init_local()

    def _parse_config(self) -> TrackedAttrConfig:
        # priority order for environment variables goes
        # cluster shell environment (read from printenv) < defaults
        # specified in global_config.ini (before this project's config
        # file was created) < vars passed to the Cluster constructor <
        # vars passed to the Project contructor < vars set after
        # creating the Project object but before submitting jobs
        use_cluster_environ = self._configparser.getboolean('runtime_environment',
                                                            'use_cluster_environ')
        if use_cluster_environ or any(self._cluster._env_additions):
            config_vars = self._configparser.get('runtime_environment', 'environ')
            config_vars = map(lambda x: x.split('='), config_vars.strip().splitlines())
            config_vars = {k.strip(): v.strip() for k, v in config_vars}
            if use_cluster_environ:
                environ_vars = self._cluster.environ.copy()
            else:
                # environ obj was constructed from and prioritizes
                # env_additions, so no need to handle situation where
                # both are True
                environ_vars = self._cluster._env_additions
            environ_vars.update(config_vars)
            # TODO: additional sources to update this with?
            environ_str = BaseConfig._environ_to_str(environ_vars)
            self._configparser.set('runtime_environment', 'environ', environ_str)
        super()._parse_config()
