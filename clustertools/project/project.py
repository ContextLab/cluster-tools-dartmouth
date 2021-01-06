from __future__ import annotations

import itertools
from pathlib import Path, PurePosixPath
from typing import (Any,
                    Dict,
                    List,
                    Literal,
                    NoReturn,
                    Optional,
                    Sequence,
                    Tuple,
                    TYPE_CHECKING,
                    Union)

from clustertools import CLUSTERTOOLS_TEMPLATES_DIR
from clustertools.file_objects.project_config import ProjectConfig
from clustertools.file_objects.project_script import ProjectScript
from clustertools.project.job import Job, JobList
from clustertools.shared.exceptions import (ClusterToolsProjectError,
                                            ProjectConfigurationError)

if TYPE_CHECKING:
    from clustertools.cluster import Cluster
    from clustertools.shared.object_monitors import MonitoredEnviron, MonitoredList
    from clustertools.shared.typing import PathLike, WallTimeStr


# TODO: add logic so that submitter is only used when there is >1 job to
#  be submitted
# TODO: allow pre-submit and collector jobs to have different n_nodes,
#  ppn, etc. from runner jobs
# TODO: write checks that will run run right before submitting
# TODO: add methods that call q___ (qdel, qsig, etc.) from pbs man page
# TODO: remember to include -C self.directive_prefix flag in submit cmd
# TODO(?): support keyword arguments to jobs via exporting as env
#  variables, types are: Union[Sequence[Sequence[Union[str, int, float]]],
#                   Sequence[Dict[str, Union[str, int, float]]],
#                   Dict[Union[str, int], Sequence[str, int, float]]]


class Project:
    # ADD DOCSTRING
    # TODO: allow passing scripts as strings? *should* be doable, if
    #  limited in functionality...
    inferred_executables = {
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
        # TODO: write me - for loading an existing project
        ...

    def __init__(
            self,
            name: str,
            cluster: Cluster,
            pre_submit_script: Optional[PathLike] = None,
            job_script: Optional[PathLike] = None,
            collector_script: Optional[PathLike] = None,
            job_params: Optional[Union[Sequence[Any], Sequence[Sequence[Any]]]] = None,
            params_as_matrix: bool = False,
            *,
            # CONFIG FIELDS SETTABLE VIA CONSTRUCTOR
            # a little egregious maybe, could wrap all these in
            # **kwargs, but IMO it's helpful to have them visible the
            # method signature & docstring
            job_basename: Optional[str] = None,
            job_executable: Optional[str] = None,
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
            notify_all_submitted: Optional[bool] = None,
            notify_all_finished: Optional[bool] = None,
            notify_job_started: Optional[bool] = None,
            notify_job_finished: Optional[bool] = None,
            notify_job_aborted: Optional[bool] = None,
            notify_job_failed: Optional[bool] = None,
            notify_collector_finished: Optional[bool] = None,
            auto_monitor_jobs: Optional[bool] = None,
            auto_resubmit_aborted: Optional[bool] = None,
            max_resubmit_attempts: Optional[int] = None,
            auto_submit_collector: Optional[bool] = None,
    ) -> None:
        self._name = name
        self._cluster = cluster
        # initialize config & update fields
        self.config = ProjectConfig(self)
        config_field_updates = {
            'job_basename': job_basename,
            'job_executable': job_executable,
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
            'all_submitted': notify_all_submitted,
            'all_finished': notify_all_finished,
            'job_started': notify_job_started,
            'job_finished': notify_job_finished,
            'job_aborted': notify_job_aborted,
            'job_failed': notify_job_failed,
            'collector_finished': notify_collector_finished,
            'auto_monitor_jobs': auto_monitor_jobs,
            'auto_resubmit_aborted': auto_resubmit_aborted,
            'max_resubmit_attempts': max_resubmit_attempts,
            'auto_submit_collector': auto_submit_collector
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
        self._init_submitter()
        if self.auto_monitor_jobs:
            self._init_monitor()
        else:
            self._monitor_script: Optional[ProjectScript] = None
            self._monitor: Optional[Job] = None
        if pre_submit_script is None:
            self._pre_submit_script: Optional[ProjectScript] = None
            self._pre_submit: Optional[Job] = None
        else:
            self.pre_submit_script = pre_submit_script
        if job_script is None:
            self._job_script: Optional[ProjectScript] = None
        else:
            self.job_script = job_script
        if collector_script is None:
            self._collector_script: Optional[ProjectScript] = None
            self._collector: Optional[Job] = None
        else:
            self.collector_script = collector_script
        # initialize job params
        self._raw_job_params = job_params
        self._params_as_matrix = params_as_matrix
        self.jobs = JobList(project=self)
        if job_params is None:
            self._job_params: Optional[List[Tuple[str]]] = None
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
    def job_executable(self) -> str:
        job_executable = self.config.general.job_executable
        if job_executable == 'INFER' and self.job_script is not None:
            return self._infer_job_executable()
        return job_executable

    @job_executable.setter
    def job_executable(self, new_cmd) -> None:
        self.config.general.job_executable = new_cmd

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
        q = self.config.pbs_params.queue
        if q == 'INFER':
            # Dartmouth Discovery cluster policy: batches of >600 jobs
            # should be submitted to largeq
            # PyCharm bug: Literals aren't detected in ternaries
            # noinspection PyTypeChecker
            return 'largeq' if len(self.jobs) > 600 else 'default'
        return q

    @queue.setter
    def queue(self, new_queue: Literal['default', 'largeq', 'INFER']) -> None:
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
    def notify_all_submitted(self) -> bool:
        return self.config.notifications.all_submitted

    @notify_all_submitted.setter
    def notify_all_submitted(self, pref: bool) -> None:
        self.config.notifications.all_submitted = pref

    @property
    def notify_all_finished(self) -> bool:
        return self.config.notifications.all_finished

    @notify_all_finished.setter
    def notify_all_finished(self, pref: bool) -> None:
        self.config.notifications.all_finished = pref

    @property
    def notify_job_started(self) -> bool:
        return self.config.notifications.job_started

    @notify_job_started.setter
    def notify_job_started(self, pref: bool) -> None:
        self.config.notifications.job_started = pref

    @property
    def notify_job_finished(self) -> bool:
        return self.config.notifications.job_finished

    @notify_job_finished.setter
    def notify_job_finished(self, pref: bool) -> None:
        self.config.notifications.job_finished = pref

    @property
    def notify_job_aborted(self) -> bool:
        return self.config.notifications.job_aborted

    @notify_job_aborted.setter
    def notify_job_aborted(self, pref: bool) -> None:
        self.config.notifications.job_aborted = pref

    @property
    def notify_job_failed(self) -> bool:
        return self.config.notifications.job_failed

    @notify_job_failed.setter
    def notify_job_failed(self, pref: bool) -> None:
        self.config.notifications.job_failed = pref

    @property
    def notify_collector_finished(self) -> bool:
        return self.config.notifications.collector_finished

    @notify_collector_finished.setter
    def notify_collector_finished(self, pref: bool) -> None:
        self.config.notifications.collector_finished = pref

    @property
    def auto_monitor_jobs(self) -> bool:
        return self.config.monitoring.auto_monitor_jobs

    @auto_monitor_jobs.setter
    def auto_monitor_jobs(self, pref: bool) -> None:
        self.config.monitoring.auto_monitor_jobs = pref
        if pref is True:
            self._init_monitor()
        else:
            self._monitor_script = None
            self._monitor = None

    @property
    def auto_resubmit_aborted(self) -> bool:
        return self.config.monitoring.auto_resubmit_aborted

    @auto_resubmit_aborted.setter
    def auto_resubmit_aborted(self, pref: bool) -> None:
        self.config.monitoring.auto_resubmit_aborted = pref

    @property
    def max_resubmit_attempts(self) -> bool:
        return self.config.monitoring.max_resubmit_attempts

    @max_resubmit_attempts.setter
    def max_resubmit_attempts(self, max_retries: int) -> None:
        self.config.monitoring.max_resubmit_attempts = max_retries

    @property
    def auto_submit_collector(self) -> bool:
        return self.config.monitoring.auto_submit_collector

    @auto_submit_collector.setter
    def auto_submit_collector(self, pref: bool) -> None:
        self.config.monitoring.auto_submit_collector = pref

    ##########################################################
    #                SCRIPT OBJECT PROPERTIES                #
    ##########################################################
    @property
    def pre_submit(self) -> Optional[Job]:
        return self._pre_submit

    @pre_submit.setter
    def pre_submit(self, *_, **__) -> NoReturn:
        raise AttributeError(
            "'project.pre_submit' attribute does not support direct assignment. "
            "Set 'project.pre_submit_script' to the path to your local script "
            "and the pre-submit 'Job' object will be regenerated automatically."
        )

    @property
    def pre_submit_script(self) -> Optional[ProjectScript]:
        return self._pre_submit_script

    @pre_submit_script.setter
    def pre_submit_script(self, script_path: Optional[PathLike]) -> None:
        # TODO: this doesn't handle a pre-submit script that takes
        #  parameters. Can't think of a good reason one would though,
        #  so fixing is low priority
        if script_path is None:
            # setting to None removes the pre-submit job
            self._pre_submit_script = self._pre_submit = None
        else:
            local_path = Path(script_path).resolve(strict=True)
            file_ext = local_path.suffix
            remote_path = self.script_dir.joinpath(f'pre_submit').with_suffix(file_ext)
            pre_submit_script = ProjectScript(project=self,
                                              local_path=local_path,
                                              remote_path=remote_path)
            self._pre_submit_script = pre_submit_script
            self._pre_submit = Job(project=self,
                                   script=pre_submit_script,
                                   kind='pre_submit')

    @property
    def submitter(self) -> Optional[Job]:
        return self._submitter

    @submitter.setter
    def submitter(self, *_, **__) -> NoReturn:
        raise AttributeError(
            "'project.submitter' attribute does not support assignment"
        )

    @property
    def submitter_script(self) -> Optional[ProjectScript]:
        return self._submitter_script

    @submitter_script.setter
    def submitter_script(self, *_, **__) -> NoReturn:
        raise AttributeError("Built-in job submitter script is not editable")

    @property
    def monitor(self) -> Optional[Job]:
        return self._monitor

    @monitor.setter
    def monitor(self, *_, **__) -> NoReturn:
        raise AttributeError(
            "'project.monitor' attribute does not support assignment"
        )

    @property
    def monitor_script(self) -> ProjectScript:
        return self._monitor_script

    @monitor_script.setter
    def monitor_script(self, *_, **__) -> NoReturn:
        raise AttributeError("Built-in job monitoring script is not editable")

    @property
    def job_script(self) -> Optional[ProjectScript]:
        return self._job_script

    @job_script.setter
    def job_script(self, script_path: Optional[PathLike]) -> None:
        if script_path is None:
            self._job_script = None
        else:
            local_path = Path(script_path).resolve(strict=True)
            file_ext = local_path.suffix
            remote_path = self.script_dir.joinpath(f'runner').with_suffix(file_ext)
            self._job_script = ProjectScript(project=self,
                                             local_path=local_path,
                                             remote_path=remote_path)
        # any change to job script means JobList cache needs to be cleared
        self.jobs.clear_cache()

    @property
    def collector(self) -> Optional[Job]:
        return self._collector

    @collector.setter
    def collector(self, *_, **__) -> NoReturn:
        raise AttributeError(
            "'project.collector' attribute does not support direct assignment. "
            "Set 'project.collector_script' to the path to your local script "
            "and the collector 'Job' object will be regenerated automatically."
        )

    @property
    def collector_script(self) -> Optional[ProjectScript]:
        return self._collector_script

    @collector_script.setter
    def collector_script(self, script_path: Optional[PathLike]) -> None:
        if script_path is None:
            self._collector = self._collector_script = None
        else:
            local_path = Path(script_path).resolve(strict=True)
            file_ext = local_path.suffix
            remote_path = self.script_dir.joinpath(f'collector').with_suffix(file_ext)
            collector_script = ProjectScript(project=self,
                                             local_path=local_path,
                                             remote_path=remote_path)
            self._collector_script = collector_script
            self._collector = Job(project=self,
                                  script=collector_script,
                                  kind='collector')

    @property
    def job_params(self) -> Optional[List[Tuple[str]]]:
        return self._job_params

    @job_params.setter
    def job_params(
            self,
            new_params: Union[Sequence[Any], Sequence[Sequence[Any]]]
    ) -> None:
        self.parametrize_jobs(new_params)

    @property
    def params_as_matrix(self) -> bool:
        return self._params_as_matrix

    @params_as_matrix.setter
    def params_as_matrix(self, as_matrix: bool) -> None:
        if as_matrix != self._params_as_matrix:
            # JobList
            if self._raw_job_params is None:
                # can't parse job params if they haven't been provided yet
                self._params_as_matrix = as_matrix
            else:
                self.parametrize_jobs(self._raw_job_params, as_matrix=as_matrix)

    ##########################################################
    #                PROJECT STATE PROPERTIES                #
    ##########################################################
    @property
    def has_active_jobs(self):
        # ADD DOCSTRING
        # TODO: write me
        raise NotImplementedError

    ##########################################################
    #                  MISC. HELPER METHODS                  #
    ##########################################################
    def _infer_job_executable(self) -> str:
        # TODO: add more options
        suffix = self.job_script.local_path.suffix
        inferred_executables = Project.inferred_executables
        inferred_executables['.sh'] = self._cluster.executable
        return inferred_executables.get(suffix, 'INFER')

    # the "submitter" and "monitor" Job & ProjectScript objects are
    # slightly different from the others. First, their scripts' contents
    # are agnostic to the purpose of the actual project/jobs. Their
    # purpose is to submit single jobs that handle long-running tasks
    # (i.e., submitting all other jobs and monitoring job progress) so
    # the local interpreter isn't blocked indefinitely. Because of this,
    # they are not meant to be editable and are read-only on the Project
    # object (to remove the monitor job, set the 'auto_monitor_jobs'
    # attribute to False. It is of course possible to edit these jobs'
    # behavior by editing their job scripts directly, this is not
    # officially supported and you should use caution in doing so.
    # Second, because their scripts' contents don't depend on the
    # project, we only need to upload a single remote copy of each for
    # all projects to share. This is done when 'clustertools' connects
    # to a new host for the first time *after which the scripts are
    # assumed to be present* to save time during job submission. The
    # remote copies are stored in the remote global config directory
    # ($HOME/.clustertools).
    def _init_monitor(self) -> None:
        local_path = CLUSTERTOOLS_TEMPLATES_DIR.joinpath('monitor.py')
        remote_path = self._cluster.config.remote_path.parent.joinpath('monitor.py')
        monitor_script = ProjectScript(project=self,
                                       local_path=local_path,
                                       remote_path=remote_path)
        self._monitor_script = monitor_script
        # TODO: this should take params based on values from
        #  ['monitoring'] section of config... will also need to update
        #  setters to update params on Job object... might be easier to
        #  set them just once based on config field at submission time
        self._monitor = Job(project=self, script=monitor_script, kind='monitor')

    def _init_submitter(self) -> None:
        local_path = CLUSTERTOOLS_TEMPLATES_DIR.joinpath('submitter.py')
        remote_path = self._cluster.config.remote_path.parent.joinpath('submitter.py')
        submitter_script = ProjectScript(project=self,
                                         local_path=local_path,
                                         remote_path=remote_path)
        self._submitter_script = submitter_script
        # NOTE: If a pre-submit job is present, the submitter job's
        # wrapper script will take the pre-submit job's jobid as a
        # param, its Job object will show self.params=None until the
        # pre-submit job is queued and its jobid is available
        self._submitter = Job(project=self, script=submitter_script, kind='submitter')

    # def configure(self):
    #     # ADD DOCSTRING - walks user through setting parameters
    #     #  interactively
    #     # TODO: write me
    #     pass

    def check_submittable(self) -> bool:
        # ADD DOCSTRING
        # returns True if all requirements to submit jobs are met
        # TODO: add check for whether or not self.pre_submit, jobs, and
        #  self.collector .expects_args
        if self.job_script is None:
            raise ClusterToolsProjectError(
                "No job script specified. Set 'project.job_script' to the path "
                "to the file you want to use to run individual jobs."
            )
        if self.job_params is None and self.job_script.expects_args:
            raise ProjectConfigurationError(
                "Failed to assemble jobs for submission: job scripts appear to "
                "expect command line arguments and no job parameters were "
                "provided. Please use 'project.parametrize_jobs()' or set "
                "'project.job_params' and 'project.params_as_matrix' to "
                "provide parameters for each job"
            )
        if self.auto_resubmit and not self.auto_monitor_jobs:
            raise ProjectConfigurationError(
                "Auto job monitoring must be enabled to automatically resubmit "
                "aborted jobs. Please set 'project.auto_monitor_jobs = True' "
                "to enable auto monitoring, or 'project.auto_resubmit = False' "
                "to disable auto resubmission"
            )
        if bool(self.env_activate_cmd) is not bool(self.env_deactivate_cmd):
            raise ProjectConfigurationError(
                "If running jobs inside a virtual environment, you must "
                "provide both a command to activate/enter the environment and "
                "a command to deactivate/exit it afterward"
            )
        if self.job_executable == 'INFER':
            raise ProjectConfigurationError(
                "Unable to infer a command for running a job script ending in "
                f"'{self.job_script.local_path.suffix}'. Please set "
                "'project.job_executable' before submitting jobs"
            )
        return True

    def parametrize_jobs(
            self,
            params: Union[Sequence[Any], Sequence[Sequence[Any]]],
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
        # clear JobList cache of Job objects created with old params
        self.jobs.clear_cache()

    ##########################################################
    #                 JOB SUBMISSION METHODS                 #
    ##########################################################
    def submit(self):
        # ADD DOCSTRING
        # TODO: write me
        # TODO: if pre-submit script, get its jobid and pass it as "$1"
        #  to submitter so it can be used with #PBS -W
        # TODO: (in submitter script) if collector is passed and
        #  config['auto_submit_collector'] is true, apply user hold to
        #  collector and have monitor script remove it once all jobs
        #  finish successfully. More straightforward than using #PBS -W
        #  and trying to determine number of jobs, accounting for
        #  restarts of monitor, resubmissions, etc.
        self.check_submittable()
        # upload new or edited scripts and write wrapper scripts
        if self.pre_submit is not None:
            self.pre_submit.script.sync()
            self._cluster.write_text(path=self.pre_submit.wrapper_path,
                                     data=self.pre_submit.wrapper)
        self._cluster.write_text(path=self.submitter.wrapper_path,
                                 data=self.submitter.wrapper)
        self._cluster.write_text(path=self.monitor.wrapper_path,
                                 data=self.monitor.wrapper)
        self.job_script.sync()
        if self.collector is not None:
            self.collector.script.sync()
            self._cluster.write_text(path=self.collector.wrapper_path,
                                     data=self.collector.wrapper)

        # import pickle
        # with self._cluster.cwd.joinpath('TEST_PICKLE.p').open('wb') as f:
        #     pickle.dump(self, f)
        # pass

    def sync_scripts(self):
        #  ADD DOCSTRING
        for script in (self.pre_submit_script, self.job_script, self.collector_script):
            if script is not None:
                script.sync()

    def write_wrappers(self):
        # ADD DOCSTRING - Creates remote wrapper scripts for submitter &
        #  pre_submit jobs only. More efficient for submitter to write
        #  wrapper scripts for runner, monitor, & collector jobs
        if self.pre_submit is not None:
            self._cluster.write_text(path=self.pre_submit.wrapper_path,
                                     data=self.pre_submit.wrapper)
        self._cluster.write_text(path=self.submitter.wrapper_path,
                                 data=self.submitter.wrapper)

        ...

