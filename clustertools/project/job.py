from typing import Iterable

from clustertools.file_objects.script import ProjectScript
from clustertools.project.project import Project


class Job:
    def __init__(
            self,
            project: Project,
            script: ProjectScript,
            params: Iterable
    ) -> None:
        self._project = project
        self.script = script
        self.params = params

    @property
    def wrapper(self):

