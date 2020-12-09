import shutil
from typing import Optional

from clustertools import CLUSTERTOOLS_CONFIG_DIR, CLUSTERTOOLS_TEMPLATES_DIR
from clustertools.cluster import Cluster
from clustertools.file_objects.base_config import BaseConfig
from clustertools.shared.typing import PathLike


class GlobalConfig(BaseConfig):
    # ADD DOCSTRING

    def __init__(self, cluster: Cluster, remote_path: Optional[PathLike] = None) -> None:
        # ADD DOCSTRING
        global_config_path_local = CLUSTERTOOLS_CONFIG_DIR.joinpath('global_config.ini')
        super().__init__(cluster=cluster,
                         local_path=global_config_path_local,
                         remote_path=remote_path)

    def _init_local(self):
        if not self.local_path.is_file():
            if not CLUSTERTOOLS_CONFIG_DIR.is_dir():
                CLUSTERTOOLS_CONFIG_DIR.mkdir()
            src = CLUSTERTOOLS_TEMPLATES_DIR.joinpath('global_config.ini')
            dest = CLUSTERTOOLS_CONFIG_DIR.joinpath('global_config.ini')
            shutil.copy2(str(src), str(dest))
