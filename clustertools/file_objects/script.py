from typing import Optional

from clustertools.cluster import Cluster
from clustertools.file_objects.synced_file import SyncedFile
from clustertools.project.project import Project
from clustertools.shared.typing import PathLike


class ProjectScript(SyncedFile):
    def __init__(
            self,
            project: Project,
            local_path: PathLike,
            remote_path: Optional[PathLike] = None
    ) -> None:
        cluster = project._cluster
        super().__init__(cluster=cluster, local_path=local_path, remote_path=remote_path)
        self.project = project

    @property
    def content(self) -> str:
        # runs on the order of microseconds for the kinds of files this
        # class will be used with, so it's worth this being a property
        # so it's always up-to-date
        return self.local_path.read_text()

    @property
    def expects_args(self) -> bool:
        content = self.content
        return (
                "sys.argv" in content
                or "from sys import argv" in content
                or "argparse" in content
        )

    def __repr__(self):
        return f'{self.local_path} -> {self.remote_path}\n\n{self.content}'