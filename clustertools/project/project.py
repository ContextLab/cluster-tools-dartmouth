from typing import Optional, Union, Dict

from clustertools.cluster import Cluster
from clustertools.configs.project_config import ProjectConfig
from clustertools.shared.typing import PathLike


class Project:
    def __init__(
            self,
            name: str,
            cluster: Cluster,
            root_dir: Optional[PathLike] = None,
            submitter: Optional[PathLike] = None,
            cruncher: Optional[PathLike] = None,
            collector: Optional[PathLike] = None,
            config: Optional[Union[PathLike, Dict, ProjectConfig]] = None,
            **config_kwargs
    ) -> None:
        self.name = name
        self.cluster = cluster
        self.root_dir = root_dir or cluster.resolve_path(self.name)
        self.submitter = submitter
        self.cruncher = cruncher
        self.collector = collector
        self.config = config
        pass
