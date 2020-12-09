from clustertools import CLUSTERTOOLS_CONFIG_DIR
from clustertools.project.project import Project
from clustertools.file_objects.base_config import BaseConfig

class ProjectConfig(BaseConfig):
    # ADD DOCSTRING
    def __init__(self, project: Project, project_name: str):
        # ADD DOCSTRING
        # currently, cluster.connected is guaranteed to be True at this point
        cluster = project.cluster
        local_path = CLUSTERTOOLS_CONFIG_DIR.joinpath(project_name, 'project_config.ini')
        # shortcut to $HOME/.clustertools/project_name/project_config.ini
        # that doesn't require running any remote commands
        remote_path = cluster.config.remote_path.parent.joinpath(project_name, 'project_config.ini')
        super().__init__(cluster=cluster, local_path=local_path, remote_path=remote_path)
        self._project = project
