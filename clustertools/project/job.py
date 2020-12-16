from __future__ import annotations

from string import Template
from typing import Dict, List, Optional, Sequence, Tuple, TYPE_CHECKING

if TYPE_CHECKING:
    from clustertools.file_objects.script import ProjectScript
    from clustertools.project.project import Project


class Job:
    def __init__(
            self,
            project: Project,
            script: ProjectScript,
            wrapper_template: Template,
            params: Optional[Sequence] = None
    ) -> None:
        self._project = project
        self.script = script
        self.params = params


class JobList(list):
    # ADD DOCSTRING
    # TODO: make this better... a lot better...
    def __init__(self, project: Project):
        self._project = project
        # self._cache = dict()

    def __getitem__(self, y):
        if isinstance(y, slice):
            # return self.__class__(self.__getitem__(y))
            raise ValueError(
                f"'{self.__class__.__name__}' object does not support slicing"
            )
        else:
            return Job(self, self._project.job_params.__getitem__(y))

    def __iter__(self):
        for i in self._project.job_params.__iter__():
            yield Job(i)

    def __len__(self):
        return len(self._project.job_params)

    def __repr__(self):
        return f"<JobList wrapper containing {len(self)} Job objects"

    def __reversed__(self):
        for i in self._project.job_params.__reversed__():
            yield Job(i)
