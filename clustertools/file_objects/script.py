from typing import Optional

from clustertools.cluster import Cluster
from clustertools.file_objects.synced_file import SyncedFile
from clustertools.shared.typing import PathLike


class ProjectScript(SyncedFile):
    def __init__(
            self,
            cluster: Cluster,
            local_path: PathLike,
            remote_path: Optional[PathLike] = None
    ):
        super().__init__(cluster=cluster, local_path=local_path, remote_path=remote_path)

    @property
    def content(self) -> str:
        # runs on the order of microseconds for the kinds of files this
        # class will be used with, so it's worth this being a property
        # so it's always up-to-date
        return self.local_path.read_text()

    def __repr__(self):
        return f'{self.local_path} -> {self.remote_path}\n\n{self.content}'