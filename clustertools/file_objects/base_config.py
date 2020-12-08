from typing import Optional

from clustertools.cluster import Cluster
from clustertools.configs.synced_file import SyncedFile
from clustertools.shared.typing import PathLike


class BaseConfig(SyncedFile):
    # ADD DOCSTRING
    def __init__(
            self,
            cluster: Cluster,
            local_path: PathLike,
            remote_path: Optional[PathLike] = None
    ) -> None:
        # ADD DOCSTRING
        super().__init__(cluster=cluster, local_path=local_path, remote_path=remote_path)

    def _init_local(self):