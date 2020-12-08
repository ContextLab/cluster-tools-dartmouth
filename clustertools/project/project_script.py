"""
class that represents submitter, cruncher, collector, etc. scripts
"""
from pathlib import Path, PurePosixPath
from typing import Optional

from clustertools.mixins.synced_file import SyncedFile
from clustertools.project.project import Project
from clustertools.shared.typing import PathLike


class ProjectScript(SyncedFile):
    def __init__(
            self,
            project: Project,
            local_path: PathLike,
            remote_path: Optional[PathLike] = None
    ):
        self.project = project
        self.local_path = Path(local_path).resolve()
        if remote_path is None:
            filename = self.local_path.name
            self.remote_path = self.project.root_dir.joinpath(filename)
        else:
            self.remote_path = self.project.cluster.resolve_path(PurePosixPath(remote_path))
        self.content = self.local_path.read_text()

    def __repr__(self):
        return f'{self.local_path} -> {self.remote_path}\n\n{self.content}'