import itertools
from pathlib import Path, PurePosixPath
from string import Template
from typing import Any, Dict, List, Literal, Optional, Sequence, Tuple, Union

from clustertools.cluster import Cluster
from clustertools.file_objects.project_config import ProjectConfig
from clustertools.file_objects.script import ProjectScript
from clustertools.project.job import Job, JobList
from clustertools.shared.exceptions import ProjectConfigurationError
from clustertools.shared.object_monitors import MonitoredEnviron, MonitoredList
from clustertools.shared.typing import PathLike, WallTimeStr
from clustertools.templates.job_wrapper import (ENV_ACTIVATE_COMMAND,
                                                ENV_DEACTIVATE_COMMAND,
                                                JOB_SUFFIX,
                                                MODULE_LOAD_COMMAND,
                                                USER_HOLD_DIRECTIVE,
                                                VAR_EXPORT_DIRECTIVE,
                                                WRAPPER_TEMPLATE)


job_params_types = Union[Sequence[Any], Sequence[Sequence[Any]]]


# TODO: write checks that will run run right before submitting
# TODO: add methods that call q___ (qdel, qsig, etc.) from pbs man page
# TODO: remember to include -C self.directive_prefix flag in submit cmd
# TODO: support keyword arguments to jobs via exporting as env variables,
#  types are: Union[Sequence[Sequence[Union[str, int, float]]],
#                   Sequence[Dict[str, Union[str, int, float]]],
#                   Dict[Union[str, int], Sequence[str, int, float]]]


class Project:
    # ADD DOCSTRING
    # TODO: allow passing scripts as strings? *should* be doable, if
    #  limited in functionality...
    inferred_cmd_wrappers = {
        '.jar': 'java -jar',
        '.jl': 'julia',
        '.m': 'matlab',
        '.pl': 'perl',
        '.py': 'python',
        '.r': 'R',
        '.rb': 'ruby',
        '.sas': 'sas',
        # '.sh': (gets assigned self.cluster.executable in the instance)
        '.swift': 'swift'
    }

    @classmethod
    def load(cls, name: str, cluster: Cluster) -> 'Project':
        ...

    def __init__(
            self,
            name: str,
            cluster: Cluster,
            pre_submit_script: Optional[PathLike] = None,
            job_script: Optional[PathLike] = None,
            collector_script: Optional[PathLike] = None,
            job_params: Optional[job_params_types] = None,
            params_as_matrix: bool = False,
            *,
            # CONFIG FIELDS SETTABLE VIA CONSTRUCTOR
            # a little egregious maybe, could wrap all these in
            # **kwargs, but IMO it's helpful to have them visible the
            # method signature & docstring
            job_basename: Optional[str] = None,
            cmd_wrapper: Optional[str] = None,
            modules: Optional[List[str]] = None,
            env_activate_cmd: Optional[str] = None,
            env_deactivate_cmd: Optional[str] = None,
            use_global_environ: Optional[bool] = None,
            environ_additions: Optional[Dict[str, str]] = None,
            directive_prefix: Optional[str] = None,
            queue: Optional[Literal['default', 'largeq']] = None,
            n_nodes: Optional[int] = None,
            ppn: Optional[int] = None,
            wall_time: Optional[WallTimeStr] = None,
            user_to_notify: Optional[str] = None,
            notify_job_start: Optional[bool] = None,
            notify_all_start: Optional[bool] = None,
            notify_job_finish: Optional[bool] = None,
            notify_all_finish: Optional[bool] = None,
            notify_job_abort: Optional[bool] = None,
            notify_job_error: Optional[bool] = None,
            auto_monitor_jobs: Optional[bool] = None,
            auto_resubmit: Optional[bool] = None
    ) -> None:
        self._name = name
        self._cluster = cluster
        # initialize config & update fields
        self.config = ProjectConfig(self)
        config_field_updates = {
            'job_basename': job_basename,
            'cmd_wrapper': cmd_wrapper,
            'modules': modules,
            'env_activate_cmd': env_activate_cmd,
            'env_deactivate_cmd': env_deactivate_cmd,
            'use_global_environ': use_global_environ,
            'directive_prefix': directive_prefix,
            'queue': queue,
            'n_nodes': n_nodes,
            'ppn': ppn,
            'wall_time': wall_time,
            'user': user_to_notify,
            'job_start': notify_job_start,
            'all_start': notify_all_start,
            'job_finish': notify_job_finish,
            'all_finish': notify_all_finish,
            'job_abort': notify_job_abort,
            'job_error': notify_job_error,
            'auto_monitor_jobs': auto_monitor_jobs,
            'auto_resubmit_jobs': auto_resubmit
        }
        config_field_updates = {
            field: val
            for field, val in config_field_updates.items()
                if val is not None and val != self.config[field]
        }
        if any(config_field_updates):
            self.config.update(config_field_updates)
        if any(environ_additions):
            self.config.environ.update(environ_additions)
        # initialize remote directory structure for project
        for remote_dir in (self.stdout_dir,
                           self.stderr_dir,
                           self.wrapper_dir,
                           self.input_datadir,
                           self.output_datadir):
            self._cluster.mkdir(remote_dir, parents=True, exist_ok=True)
        # initialize script objects
        self._raw_wrapper_template = WRAPPER_TEMPLATE
        if pre_submit_script is None:
            self._pre_submit_script = None
        else:
            self.pre_submit_script = pre_submit_script
        if job_script is None:
            self._job_script = None
        else:
            self.job_script = job_script
        if collector_script is None:
            self._collector_script = None
        else:
            self.collector_script = collector_script

        # initialize job params
        self._raw_job_params = job_params
        self._params_as_matrix = params_as_matrix
        if job_params is None:
            self._job_params = None
            self.jobs: Optional[JobList] = None
        else:
            self.parametrize_jobs(job_params, as_matrix=params_as_matrix)

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, new_name):
        # TODO: write this. Don't allow rename if any jobs in progress.
        #  Otherwise, change project dirname and all other info that
        #  reflects project name
        ...
        self._name = new_name

    ##########################################################
    #                 CONFIG-DEPENDENT PATHS                 #
    ##########################################################
    # name, root_dir, input_datadir, output_datadir, and script_dir are
    # constructed on-the-fly like this so that:
    #  - they can be kept in sync with the relevant fields in self.config
    #  - changing each of these path components involves a slightly
    #    different 'mv'/'rename' command, and dealing with them separately
    #    makes the corresponding code much simpler
    #  - property setup prevents users from changing multiple components
    #    at once (e.g., just setting self.input_datadir to something totally
    #    different) which would be difficult to code around defensively
    #  - path components are simpler to store when unloading project,
    #    quicker update on global config field change while project is
    #    unloaded, and easier to reconstruct when reloading later
    @property
    def root_dir(self) -> PurePosixPath:
        return self._cluster.config.general.project_dir.joinpath(self.name)

    @property
    def input_datadir(self) -> PurePosixPath:
        return self.root_dir.joinpath(self.config.general.input_datadir)

    @property
    def output_datadir(self) -> PurePosixPath:
        return self.root_dir.joinpath(self.config.general.output_datadir)

    @property
    def script_dir(self) -> PurePosixPath:
        return self.root_dir.joinpath('scripts')

    @property
    def stderr_dir(self) -> PurePosixPath:
        return self.script_dir.joinpath('stderr')

    @property
    def stdout_dir(self) -> PurePosixPath:
        return self.script_dir.joinpath('stdout')

    @property
    def wrapper_dir(self) -> PurePosixPath:
        return self.script_dir.joinpath('wrappers')

    ##########################################################
    #           OTHER CONFIG-DEPENDENT PROPERTIES            #
    ##########################################################
    # making these attributes properties allows them to be linked
    # directly to the relevant config fields so that:
    #  - they never get out of sync with the file, whether changes are
    #    made within python to the object attrs or the config object,
    #    or directly to the config file
    #  - their setters can use the validation functions already assigned
    #    to run when updating the config fields
    #  - more info about this object is accessible via the config file,
    #    saving overhead when saving & reloading project state
    @property
    def job_basename(self) -> str:
        basename = self.config.general.job_basename
        return self.name if basename == 'INFER' else basename

    @job_basename.setter
    def job_basename(self, new_name: str) -> None:
        self.config.general.job_basename = new_name

    @property
    def cmd_wrapper(self) -> str:
        cmd_wrapper = self.config.general.cmd_wrapper
        if cmd_wrapper == 'INFER' and self.job_script is not None:
            return self._infer_cmd_wrapper()
        return cmd_wrapper

    @cmd_wrapper.setter
    def cmd_wrapper(self, new_cmd) -> None:
        self.config.general.cmd_wrapper = new_cmd

    @property
    def modules(self) -> MonitoredList:
        return self.config.runtime_environment.modules

    @modules.setter
    def modules(self, new_module_list: List[str]) -> None:
        new_module_list = MonitoredList(new_module_list,
                                        update_hook=self.config._modules_update_hook)
        self.config.runtime_environment.modules = new_module_list

    @property
    def env_activate_cmd(self) -> str:
        return self.config.runtime_environment.env_activate_cmd

    @env_activate_cmd.setter
    def env_activate_cmd(self, new_cmd: str) -> None:
        self.config.runtime_environment.env_activate_cmd = new_cmd

    @property
    def env_deactivate_cmd(self) -> str:
        return self.config.runtime_environment.env_deactivate_cmd

    @env_deactivate_cmd.setter
    def env_deactivate_cmd(self, new_cmd: str) -> None:
        self.config.runtime_environment.env_deactivate_cmd = new_cmd

    @property
    def use_global_environ(self) -> bool:
        return self.config.runtime_environment.use_global_environ

    @use_global_environ.setter
    def use_global_environ(self, use: bool) -> None:
        self.config.runtime_environment.use_global_environ = use
        
    @property
    def environ(self) -> MonitoredEnviron:
        return self.config.runtime_environment.environ

    @property
    def directive_prefix(self) -> str:
        prefix = self.config.pbs_params.directive_prefix
        if prefix == 'INFER':
            prefix = self.config.runtime_environment.environ.get('PBS_DPREFIX', 'PBS')
        return prefix

    @directive_prefix.setter
    def directive_prefix(self, new_prefix: str) -> None:
        self.config.pbs_params.directive_prefix = new_prefix

    @property
    def queue(self) -> Literal['default', 'largeq']:
        return self.config.pbs_params.queue

    @queue.setter
    def queue(self, new_queue: Literal['default', 'largeq']) -> None:
        self.config.pbs_params.queue = new_queue

    @property
    def n_nodes(self) -> int:
        return self.config.pbs_params.n_nodes

    @n_nodes.setter
    def n_nodes(self, new_nnodes: int) -> None:
        self.config.pbs_params.n_nodes = new_nnodes

    @property
    def ppn(self) -> int:
        return self.config.pbs_params.ppn

    @ppn.setter
    def ppn(self, new_ppn: int) -> None:
        self.config.pbs_params.ppn = new_ppn

    @property
    def wall_time(self) -> WallTimeStr:
        return self.config.pbs_params.wall_time

    @wall_time.setter
    def wall_time(self, new_walltime: WallTimeStr) -> None:
        self.config.pbs_params.wall_time = new_walltime

    @property
    def user_to_notify(self) -> str:
        user = self.config.notifications.user
        return self._cluster.username if user == 'INFER' else user

    @user_to_notify.setter
    def user_to_notify(self, new_user: str) -> None:
        self.config.notifications.user = new_user

    @property
    def notify_job_start(self) -> bool:
        return self.config.notification.job_start

    @notify_job_start.setter
    def notify_job_start(self, pref: bool) -> None:
        self.config.notification.job_start = pref

    @property
    def notify_all_start(self) -> bool:
        return self.config.notification.all_start

    @notify_all_start.setter
    def notify_all_start(self, pref: bool) -> None:
        self.config.notification.all_start = pref

    @property
    def notify_job_finish(self) -> bool:
        return self.config.notification.job_finish

    @notify_job_finish.setter
    def notify_job_finish(self, pref: bool) -> None:
        self.config.notification.job_finish = pref

    @property
    def notify_all_finish(self) -> bool:
        return self.config.notification.all_finished

    @notify_all_finish.setter
    def notify_all_finish(self, pref: bool) -> None:
        self.config.notification.all_finished = pref

    @property
    def notify_job_abort(self) -> bool:
        return self.config.notification.job_aborted

    @notify_job_abort.setter
    def notify_job_abort(self, pref: bool) -> None:
        self.config.notification.job_aborted = pref

    @property
    def notify_job_error(self) -> bool:
        return self.config.notifications.job_error

    @notify_job_error.setter
    def notify_job_error(self, pref):
        self.config.notifications.job_error = pref

    @property
    def auto_monitor_jobs(self) -> bool:
        return self.config.monitoring.auto_monitor_jobs

    @auto_monitor_jobs.setter
    def auto_monitor_jobs(self, pref: bool) -> None:
        self.config.monitoring.auto_monitor_jobs = pref

    @property
    def auto_resubmit(self) -> bool:
        return self.config.monitoring.auto_resubmit_aborted

    @auto_resubmit.setter
    def auto_resubmit(self, pref: bool) -> None:
        self.config.monitoring.auto_resubmit_aborted = pref

    ##########################################################
    #                SCRIPT OBJECT PROPERTIES                #
    ##########################################################
    @property
    def pre_submit_script(self) -> ProjectScript:
        return self._pre_submit_script

    @pre_submit_script.setter
    def pre_submit_script(self, script_path: PathLike) -> None:
        local_path = Path(script_path).resolve(strict=True)
        file_ext = local_path.suffix
        remote_path = self.script_dir.joinpath(f'pre_submit').with_suffix(file_ext)
        self._pre_submit_script = ProjectScript(cluster=self._cluster,
                                                local_path=local_path,
                                                remote_path=remote_path)

    @property
    def job_script(self) -> ProjectScript:
        return self._job_script

    @job_script.setter
    def job_script(self, script_path: PathLike) -> None:
        local_path = Path(script_path).resolve(strict=True)
        file_ext = local_path.suffix
        remote_path = self.script_dir.joinpath(f'runner').with_suffix(file_ext)
        self._job_script = ProjectScript(cluster=self._cluster,
                                         local_path=local_path,
                                         remote_path=remote_path)

    @property
    def collector_script(self) -> ProjectScript:
        return self._collector_script

    @collector_script.setter
    def collector_script(self, script_path: PathLike) -> None:
        local_path = Path(script_path).resolve(strict=True)
        file_ext = local_path.suffix
        remote_path = self.script_dir.joinpath(f'collector').with_suffix(file_ext)
        self._collector_script = ProjectScript(cluster=self._cluster,
                                               local_path=local_path,
                                               remote_path=remote_path)

    @property
    def wrapper_template(self):
        # first, fill the top-level template with the correct
        # sub-templates
        subtemplates = dict()
        if any(self.environ):
            subtemplates['environ_exporter'] = VAR_EXPORT_DIRECTIVE.template
        else:
            subtemplates['environ_exporter'] = ""
        if any(self.modules):
            subtemplates['module_loader'] = MODULE_LOAD_COMMAND.template
        else:
            subtemplates['module_loader'] = ""
        if self.env_activate_cmd or self.env_deactivate_cmd:
            subtemplates['virtual_env_activator'] = ENV_ACTIVATE_COMMAND
            subtemplates['virtual_env_deactivator'] = ENV_DEACTIVATE_COMMAND
        else:
            subtemplates['virtual_env_activator'] = ""
            subtemplates['virtual_env_deactivator'] = ""
        wrapper_template = Template(self._raw_wrapper_template.safe_substitute(subtemplates))
        # next, fill non-job-specific fields
        substitutions = {
            'directive_prefix': self.directive_prefix,
            'job_basename': self.job_basename,
            'project_root': self.root_dir,
            'stdout_dir': self.stdout_dir,
            'stderr_dir': self.stderr_dir,
            'environ_vars': ','.join('='.join(i) for i in self.environ.items()),
            'queue': self.queue,
            'n_nodes': self.n_nodes,
            'ppn': self.ppn,
            'wall_time': self.wall_time,
            'user': self.user_to_notify,
            # 'mail_options': self._get_mail_options(),
            'modules': ' '.join(self.modules),
            'activate_cmd': self.env_activate_cmd,
            'cmd_wrapper': self.cmd_wrapper,
            'deactivate_cmd': self.env_deactivate_cmd
        }


    @property
    def job_params(self) -> List[Tuple[str]]:
        return self._job_params

    @job_params.setter
    def job_params(self, new_params: job_params_types) -> None:
        self.parametrize_jobs(new_params)
        
    @property
    def params_as_matrix(self) -> bool:
        return self._params_as_matrix

    @params_as_matrix.setter
    def params_as_matrix(self, as_matrix: bool) -> None:
        if as_matrix != self._params_as_matrix:
            if self._raw_job_params is None:
                # can't parse job params if they haven't been provided yet
                self._params_as_matrix = as_matrix
            else:
                self.parametrize_jobs(self._raw_job_params, as_matrix=as_matrix)

    def _get_mail_options(self) -> str:
        mail_option_str = ''
        if self.notify_job_abort:
            mail_option_str += 'a'
        if self.notify_job_start:
            mail_option_str += 'b'
        if self.notify_job_finish:
            mail_option_str += 'e'
        if self.notify_job_error:
            mail_option_str += 'f'
        if  mail_option_str == '':
            mail_option_str = 'n'
        return mail_option_str

    def _infer_cmd_wrapper(self) -> str:
        # TODO: add more options
        jobscript_ext = self.job_script.local_path.suffix
        cmd_wrappers = Project.inferred_cmd_wrappers
        cmd_wrappers['.sh'] = self._cluster.executable
        return cmd_wrappers.get(jobscript_ext, 'INFER')

    # def configure(self):
    #     # ADD DOCSTRING - walks user through setting parameters
    #     #  interactively
    #     # TODO: write me
    #     pass

    def check_submittable(self) -> bool:
        # returns True if all requirements to submit are met
        if self.auto_resubmit and not self.auto_monitor_jobs:
            raise ProjectConfigurationError(
                "Auto job monitoring must be enabled to automatically resubmit "
                "aborted jobs. Please set the 'project.auto_monitor_jobs = True' "
                "to enable auto monitoring, or 'project.auto_resubmit = False' "
                "to disable auto resubmission"
            )
        if bool(self.env_activate_cmd) is not bool(self.env_deactivate_cmd):
            raise ProjectConfigurationError(
                "If running jobs inside a virtual environment, you must "
                "provide both a command to activate/enter the environment and "
                "a command to deactivate/exit it afterward"
            )
        if self.cmd_wrapper == 'INFER':
            raise ProjectConfigurationError(
                "Unable to infer a command for running a job script ending in "
                f"'{self.job_script.local_path.suffix}'. Please set "
                "'project.cmd_wrapper' before submitting jobs"
            )
        if self.job_params is None and self.job_script.expects_args:
            raise ProjectConfigurationError(
                "Failed to assemble jobs for submission: job scripts appear to "
                "expect command line arguments and no job parameters were "
                "provided. Please use the 'project.parametrize_jobs()' or set "
                "'project.job_params' and 'project.params_as_matrix' to "
                "provide parameters for each job"
            )
        return True

    def parametrize_jobs(
            self,
            params: job_params_types,
            *,
            as_matrix: Optional[bool] = None
    ) -> None:
        if as_matrix is None:
            as_matrix = self._params_as_matrix
        else:
            self._params_as_matrix = as_matrix
        if not hasattr(params[0], '__iter__') or isinstance(params[0], str):
            params = [(str(param_val),) for param_val in params]
        else:
            params = [tuple(map(str, param_vals)) for param_vals in params]
        if as_matrix:
            params = list(itertools.product(*params))
        self._job_params = params
        self.jobs = JobList(self)

    def submit(self):
        print('time to submit!')
        import pickle
        with self._cluster.cwd.joinpath('TEST_PICKLE.p').open('wb') as f:
            pickle.dump(self, f)




################################################################################


class SimpleDefaultDict(dict):
    # ADD DOCSTRING
    """
    Similar to collections.defaultdict, but doesn't add missing keys.
    Accepts an additional keyword-only argument 'default' that may
    be either a default value to return for missing keys, or a
    callable that accepts the missing key as an argument
    """
    def __init__(self, *arg, default='?', **kwargs):
        # ADD DOCSTRING
        if len(arg) > 1:
            raise TypeError(
                f"{self.__class__.__name__} expected at most 1 argument, got "
                f"{len(arg)}"
            )
        super().__init__(*arg, **kwargs)
        if callable(default):
            self.default = default
        else:
            self.default = lambda key: default

    def __missing__(self, key):
        return self.default(key)
