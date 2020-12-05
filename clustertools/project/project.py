from typing import Optional

from clustertools.cluster import Cluster
from clustertools.shared.typing import PathLike


class Project:
    def __init__(
            self,
            name: str,
            cluster: Cluster,
            root_dir: Optional[PathLike] = None,
            submitter_script: Optional[PathLike] = None,
            job_script: Optional[PathLike] = None,
            collector_script: Optional[PathLike] = None,
            config: Optional[PathLike] = None,
            **config_kwargs
    ) -> None:
        self.name = name
        self.cluster = cluster
        self.root_dir = root_dir or cluster.resolve_path(self.name)

        pass

    @property
