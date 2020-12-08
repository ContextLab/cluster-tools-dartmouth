from typing import Optional

from clustertools import CLUSTERTOOLS_CONFIG_DIR
from clustertools.cluster import Cluster
from clustertools.configs.base_config import BaseConfig
from clustertools.shared.typing import PathLike


class GlobalConfig(BaseConfig):
    def __init__(
            self,
            cluster: Cluster,
            remote_path: Optional[PathLike]
    ):
        global_config_path_local = CLUSTERTOOLS_CONFIG_DIR.joinpath('global_config.ini')
        super().__init__(cluster=cluster,
                         local_path=global_config_path_local,
                         remote_path=remote_path)
