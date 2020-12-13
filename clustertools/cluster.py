import os
from pathlib import PurePosixPath
from typing import Optional, Tuple

from clustertools import CLUSTERTOOLS_CONFIG_DIR
from clustertools.file_objects.global_config import GlobalConfig
from clustertools.project.project import Project
from clustertools.project.project_handler import ProjectHandlerMixin
from clustertools.shells.base_shell import BaseShell
from clustertools.shared.exceptions import ClusterToolsProjectError, SSHConnectionError
from clustertools.shared.typing import NoneOrMore

# clustertools config directory structure
#  $HOME
#  └── .clustertools/
#      ├── global_config.ini
#      ├── project_name_1/
#      │   └── .project_config.ini
#      ├── project_name_2/
#      │   └── .project_config.ini
#      └── ...


class Cluster(BaseShell):
    # ADD DOCSTRING
    def __init__(
            self,
            hostname: str,
            username: Optional[str] = None,
            password: Optional[str] = None,
            connect: bool = True,
            **shell_kwargs
    ) -> None:
        # ADD DOCSTRING
        _local = hostname == 'localhost'
        if _local:
            raise NotImplementedError("Configuration for local deployment is "
                                      "not yet fully supported")
        self.config = GlobalConfig(cluster=self)
        cwd = shell_kwargs.pop('cwd', None)
        if cwd is None and self.config.general.launch_in_project_dir:
            cwd = self.config.general.project_dir
        executable = shell_kwargs.pop('executable', self.config.general.executable)
        env_additions = shell_kwargs.pop('env_additions', None)
        port = shell_kwargs.pop('port', None)
        super().__init__(hostname=hostname,
                         username=username,
                         password=password,
                         cwd=cwd,
                         executable=executable,
                         env_additions=env_additions,
                         port=port,
                         connect=False,
                         _local=_local)
        if connect and not _local:
            self.connect(**shell_kwargs)
        self.project = None
        self._all_projects = tuple(next(os.walk(CLUSTERTOOLS_CONFIG_DIR))[1])


    # TODO: define __eq__ and __isinstancecheck__ methods since dynamic
    #  retyping breaks type checks

    ##########################################################
    #                     INITIALIZATION                     #
    ##########################################################
    def connect(
            self,
            hostname: Optional[str] = None,
            username: Optional[str] = None,
            password: Optional[str] = None,
            use_key: bool = False,
            port: Optional[int] = None,
            timeout: int = 60,
            retries: int = 0,
            retry_delay: int = 1
    ) -> None:
        # ADD DOCSTRING
        # TODO(?): after connecting, check all local project dirs exist
        #  on remote and are synced (checksums match)
        super().connect(hostname=hostname,
                        username=username,
                        password=password,
                        use_key=use_key,
                        port=port,
                        timeout=timeout,
                        retries=retries,
                        retry_delay=retry_delay)
        remote_home = PurePosixPath(self.getenv('HOME'))
        self.config.remote_path = remote_home.joinpath('.clustertools/global_config.ini')

    ##########################################################
    #                   PROJECT MANAGEMENT                   #
    ##########################################################
    @property
    def all_projects(self):
        return self._all_projects

    def _mixin_project(self):
        # adds functionality that simplify interfacing with a Project
        cls = self.__class__
        cls_name = 'ClusterProjectHandler'  # cls.__name__
        cls_bases = (ProjectHandlerMixin, *cls.__bases__)
        self.__class__ = type(cls_name, cls_bases, dict(cls.__dict__))

    def _mixout_project(self):
        # removes single Project-related functionality
        self.__class__ = Cluster
        # TODO: delattr the instance attributes

    def create_project(self, name: str, **kwargs):
        # ADD DOCSTRING - creates a new project configuration & an entry
        #  in $HOME/.clustertools
        # TODO: should take all (or most) arguments in Project constructor
        # TODO: would be possible to allow creating/partially loading
        #  projects before connecting, but would require a lot of
        #  additional coding around possible scenarios
        if not self.connected:
            raise SSHConnectionError("SSH connection must be open to create a project")
        elif self.project is not None:
            raise ClusterToolsProjectError(
                "Cannot create a project when one is already loaded. Use "
                "'cluster.unload_project()' to unload the current project "
                "before creating a new one."
            )
        elif name in self.all_projects:
            raise ClusterToolsProjectError(
                f"Project '{name}' already exists. Use "
                f"cluster.load_project('{name}') to load its previous state."
            )
        self.project = Project(name=name, cluster=self, **kwargs)
        self._all_projects = tuple(list(self._all_projects) + [self.project.name])
        self._mixin_project()

    def load_project(self, name: str):
        # ADD DOCSTRING
        # loads a project form $HOME/.clustertools
        if not self.connected:
            raise SSHConnectionError("SSH connection must be open to load a project")
        elif self.project is not None:
            raise ClusterToolsProjectError(
                f"Project '{self.project.name}' is already loaded. Use "
                "'cluster.unload_project()' to unload the current project "
                "before loading a new one"
            )
        self.project = Project.load(name=name, cluster=self)
        self._mixin_project()

    def delete_project(self, name: str, yes: Optional[bool] = None, force: bool = False):
        # ADD DOCSTRING - note that:
        #  - manually setting 'yes' to either True or False overrides
        #    value of general.confirm_project_deletion in global config
        #  - passing 'force=True' is like passing 'yes=True' but ALSO
        #    will delete the project even if it's loaded and/or has
        #    running jobs (jobs will be stopped)
        # TODO: write main body
        # removes a project configuration in $HOME/.clustertools
        # warns if not all jobs completed & prompts to confirm always
        if force:
            if yes is False:
                raise ValueError("Cannot pass both 'yes=False' and 'force=True'")
            else:
                yes = True
        elif yes is None:
            yes = self.config.general.confirm_project_deletion
        if self.project is not None and self.project.name == name:
            if force:
                self.unload_project()
            else:
                raise ClusterToolsProjectError(
                    f"Project '{self.project.name}' is currently loaded. Use "
                    "'cluster.unload_project()' to unload the project before "
                    "deleting (or pass 'force=True')"
                )
        # check if project has running jobs
        # if project has running jobs
            # if force
                # stop all jobs (killthemall)
            # else
                # raise ClusterToolsProjectError
        # if not yes:
            # confirmed = prompt for y/n "are you sure ______"
        # else:
            # confirmed = True
        # if confirmed:
            # delete relevant files and directories
        ...
        _projs = list(self._all_projects)
        _projs.remove(name)
        self._all_projects = tuple(_projs)

    def unload_project(self, save_state: bool = True):
        # ADD DOCSTRING - note that user should never set 'save_state'
        #  to False unless they're planning to delete the project
        #  immediately after unloading
        # TODO: write me
        # unloads the current project and "mixes out" the ProjectMixin
        ...
        self._mixout_project()
        pass

    def status(self, projects: NoneOrMore[str] = None):
        # ADD DOCSTRING
        # TODO: write me
        # displays status info for jobs associated with one,
        # multiple, or [default] all projects
        pass



    ##########################################################
    #                     JOB SUBMISSION                     #
    ##########################################################
    def submit(self, **kwargs):
        pass

    ##########################################################
    #                     JOB MONITORING                     #
    ##########################################################
    def monitor(self):
        pass

    def killthemall(self):
        # Hi @Tudor :)
        pass

    ##########################################################
    #                 JOB OUTPUT COLLECTION                  #
    ##########################################################
