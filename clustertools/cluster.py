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
#      ├── project_config.ini
#      └── projects/
#          ├── projectname1.ini
#          ├── projectname2.ini
#          └── ...


class Cluster(BaseShell):
    # ADD DOCSTRING
    def __init__(
            self,
            hostname: str,
            username: Optional[str] = None,
            password: Optional[str] = None,
            connect: bool = False,
            **ssh_kwargs
    ) -> None:
        # ADD DOCSTRING
        _local = hostname == 'localhost'
        if _local:
            raise NotImplementedError("Configuration for local deployment is "
                                      "not yet fully supported")

        self.config = GlobalConfig(cluster=self)
        cwd = ssh_kwargs.pop('cwd', self.config.project_dir)
        executable = ssh_kwargs.pop('executable', self.config.executable)
        env_additions = ssh_kwargs.pop('env_additions', None)
        port = ssh_kwargs.pop('port', None)
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
            self.connect(**ssh_kwargs)

        self.project = None

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
        # NOTE: when connecting, need to initialize with CWD set to $HOME,
        # then switch to remote_root in case it doesn't exist
        #
        # FOLLOW UP NOTE: why did I think I needed to do this? Was it so
        # the user could connect with cwd set to the dir for a new
        # project, and it'd be created before chdir'ing there? Probably
        # not a good idea, since typos are much more likely and standard
        # use will be using global config

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
    def all_projects(self) -> Tuple[str]:
        # ADD DOCSTRING - returns a tuple of existing remote projects
        try:
            return self._cache['all_projects']
        except KeyError:
            projects = tuple(str(i.name) for i in CLUSTERTOOLS_CONFIG_DIR.iterdir() if i.is_dir())
            self._cache['all_projects'] = projects
            return self._cache['all_projects']

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
        # TODO: would be possible to allow creating/partially loading
        #  projects before connecting, but would require a lot of
        #  additional coding around possible scenarios
        if not self.connected:
            raise SSHConnectionError("SSH connection must be open to create "
                                     "or load projects")
        elif self.project is not None:
            raise ClusterToolsProjectError(
                "Cannot create a project when one is already loaded. Use "
                "'Cluster.unload_project()' to unload the current project "
                "before creating a new one."
            )
        elif name in self.all_projects:
            raise ClusterToolsProjectError(f"Project '{name}' already exists."
                                           f"Use Cluster.load_project('{name}') "
                                           "to load its previous state.")
        self.project = Project(name=name, cluster=self, )





    def load_project(self, name: str):
        # loads a prjoect form $HOME/.clustertools
        if not self.connected:
            raise SSHConnectionError("SSH connection must be open to create "
                                     "or load projects")
        elif

        pass

    def remove_project(self, name: str):
        # removes a project configuration in $HOME/.clustertools
        # warns if not all jobs completed & prompts to confirm always
        ...
        self._cache.pop('all_projects')
        pass

    def unload_project(self):
        # unloads the current project and "mixes out" the ProjectMixin
        pass

    def status(self, projects: NoneOrMore[str] = None):
        # displays status info for jobs associated with one,
        # multiple, or [default] all projects
        pass






    def _auto_detect_notebook(self):
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

    ##########################################################
    #                 JOB OUTPUT COLLECTION                  #
    ##########################################################
