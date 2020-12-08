from pathlib import Path
from typing import Optional, Tuple

from clustertools.configs.global_config import GlobalConfig
from clustertools.mixins.project_handler import ProjectHandlerMixin
from clustertools.shells.base_shell import BaseShell
from clustertools.shared.exceptions import ClusterProjectError, SSHConnectionError
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

        cwd = ssh_kwargs.pop('cwd', None)
        executable = ssh_kwargs.pop('executable', None)
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
        _cwd = self.cwd
        self.cwd = None
        try:
            super().connect(hostname=hostname,
                            username=username,
                            password=password,
                            use_key=use_key,
                            port=port,
                            timeout=timeout,
                            retries=retries,
                            retry_delay=retry_delay)
        finally:

            # skip validation because we're just replacing it
            self._cwd = _cwd





    ##########################################################
    #                   PROJECT MANAGEMENT                   #
    ##########################################################
    @property
    def all_projects(self) -> Tuple[str]:
        # ADD DOCSTRING - returns a tuple of existing remote projects
        if not self.connected:
            raise SSHConnectionError("SSH connection must be open to read active projects")
        else:
            try:
                return self._cache['all_projects']
            except KeyError:
                projects = tuple(self.listdir('~/.clustertools/projects').split())
                self._cache['all_projects'] = projects
                return projects

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

    def create_project(self, name: str):
        # ADD DOCSTRING - creates a new project configuration & an entry
        #  in $HOME/.clustertools
        if not self.connected:
            raise SSHConnectionError("SSH connection must be open to create "
                                     "or load projects")
        elif self.project is not None:
            raise ClusterProjectError(
                "Cannot create a project when one is already loaded. Use "
                "'Cluster.unload_project()' to unload the current project "
                "before creating a new one."
            )




    def load_project(self, name: str):
        # loads a prjoect form $HOME/.clustertools

        self.chdir()
        pass

    def remove_project(self, name: str):
        # removes a project configuration in $HOME/.clustertools
        # warns if not all jobs completed & prompts to confirm always
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

# remote_root: Optional[PathLike] = None,
# data_dir: PathLike = 'data',
# script_dir: PathLike = 'scripts',
# modules: NoneOrMore[str] = None,
# env_type: Optional[str] = None,
# env_name: Optional[str] = None,
# command_wrapper: Optional[str] = None,
# batch_name: Optional[str] = None,  # default to username?
# queue: str = 'largeq',
# n_nodes: int = 1,
# ppn: int = 1,
# wall_time: str = '1:00:00',
# notify_on: Optional[str] = None,  # TODO: find out default value
# notify_at: Optional[str] = None,  # TODO: find out default value



        # init SSH connection
        # super().__init__(hostname=hostname, username=username, password=password, **ssh_shell_kwargs)

    #     # project structure setup
    #     self._remote_root = None
    #     self._data_subdir = PurePosixPath(data_dir)
    #     self._script_subdir = PurePosixPath(script_dir)
    #     if remote_root is not None:
    #         self.remote_root = PurePosixPath(remote_root)
    #         self.data_dir = self.remote_root.joinpath(self._data_subdir)
    #         self.script_dir = self.remote_root.joinpath(self._script_subdir)
    #         self.data_dir.mkdir(parents=True, exist_ok=True)
    #         self.script_dir.mkdir(parents=True, exist_ok=True)
    #     else:
    #         self.remote_root = None
    #         self.data_dir = None
    #         self.script_dir = None
    #
    # @property
    # def remote_root(self):
    #     return self._remote_root
    #
    # @remote_root.setter
    # def remote_root(self, new_root: PathLike):
    #     if not isinstance(new_root, (str, PosixPath, PurePosixPath)):
    #         raise AttributeError("Must be a str or POSIX-compatible Path object")
    #
    #     new_root = PurePosixPath(new_root)
    #     if not new_root.is_absolute():
    #         raise AttributeError("'remote_root' must be an absolute path")
    #
    #
    #
    #
    #














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
