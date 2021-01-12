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
from clustertools.file_objects.configs.project_config import ProjectConfig
from clustertools.file_objects.project_script import ProjectScript
from clustertools.project.job import Job, JobList
from clustertools.shared.exceptions import (ClusterToolsProjectError,
                                            ProjectConfigurationError)

if TYPE_CHECKING:
    from clustertools.cluster import Cluster
    from clustertools.shared.object_monitors import MonitoredEnviron, MonitoredList
    from clustertools.shared.typing import (EmailAddress,
                                            NoneOrMore,
                                            PathLike,
                                            WallTimeStr)


# TODO: add logic so that submitter is only used when there is >1 job to
#  be submitted
# TODO: allow pre-submit and collector jobs to have different n_nodes,
#  ppn, etc. from runner jobs
# TODO: write checks that will run run right before submitting
# TODO: add methods that call q___ (qdel, qsig, etc.) from pbs man page
# TODO: remember to include -C self.config.directive_prefix flag in
#  submit cmd
# TODO(?): support keyword arguments to jobs via exporting as env
#  variables, types are: Union[Sequence[Sequence[Union[str, int, float]]],
#                   Sequence[Dict[str, Union[str, int, float]]],
#                   Dict[Union[str, int], Sequence[str, int, float]]]


class Project:
    # ADD DOCSTRING
    # TODO: allow passing scripts as strings? *should* be doable, if
    #  limited in functionality...

    _inferred_executables = {
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
            **config_kwargs
    ) -> None:
        self._name = name
        self._cluster = cluster
        # initialize config & update fields
        self._config = ProjectConfig(self)
        if any(config_kwargs):
            self.config.update(config_kwargs)
        # initialize remote directory structure for project
        for remote_dir in (self.stdout_dir,
                           self.stderr_dir,
                           self.wrapper_dir,
                           self.input_datadir,
                           self.output_datadir):
            self._cluster.mkdir(remote_dir, parents=True, exist_ok=True)
        # initialize script objects
        self._init_submitter()
        if self.config.monitoring.auto_monitor_jobs:
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
    def config(self) -> ProjectConfig:
        return self._config

    @config.setter
    def config(self, _: Any) -> NoReturn:
        raise AttributeError(
            "Cannot overwrite ProjectConfig object. To update "
            "configuration fields, use 'project.configure()' or set "
            "attributes on 'project.config' directly"
        )

    @config.deleter
    def config(self) -> NoReturn:
        raise AttributeError("Cannot delete 'project.config' attribute")

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, new_name):
        # TODO: write this. Don't allow rename if any jobs in progress.
        #  Otherwise, change project dirname and all other info that
        #  reflects project name
        # TODO: this should also update the relevant files/paths both
        #  locally and remotely to reflect the new name
        ...
        if self.config.general.job_basename == self.name:
            # update job basename to new project name if not explicitly
            # set to something else
            self.config.general.job_basename = new_name
        self._name = new_name


    ####################################################################
    #                         PATH PROPERTIES                          #
    ####################################################################
    # name, root_dir, input_datadir, output_datadir, and script_dir are
    # constructed on-the-fly like this so that:
    #  - they can be kept in sync with the relevant fields in
    #    self.config and self._cluster.config
    #  - changing each of these path components involves a slightly
    #    different 'mv'/'rename' command, and dealing with them
    #    separately makes the corresponding code much simpler
    #  - property setup prevents users from changing multiple components
    #    at once (e.g., just setting self.input_datadir to something
    #    totally different) which would be difficult to code around
    #    defensively
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

    ####################################################################
    #            CONFIG FIELDS ACCESSIBLE ON PROJECT OBJECT            #
    ####################################################################
    # These are likely to be frequently accessed and from an API
    # standpoint make sense as attributes of the Project itself.
    # Written as properties to ensure changes made here, to the config
    # object, and directly to the config file are reflected in all three
    # places
    @property
    def environ(self) -> MonitoredEnviron:
        return self.config.runtime_environment.environ

    @environ.setter
    def environ(self, env_dict: Dict[str, str]) -> None:
        # validation and conversion to MonitoredEnviron handled by
        # TrackedAttrConfig update hook
        self.config.runtime_environment.environ = env_dict

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

    ####################################################################
    #                     CONFIG "<INFER>" HELPERS                     #
    ####################################################################
    # methods that handle filling values for project config fields that
    # default to "INFER", so their values can be determined based on
    # other fields or properties of the Project object
    # def _infer_job_basename(self) -> str:
    #     basename = self.config.general.job_basename
    #     return self.name if basename == '<INFER>' else basename

    def _infer_job_executable(self) -> str:
        # TODO: add more options to Project._inferred_executables
        suffix = self.job_script.local_path.suffix
        if suffix == '.sh':
            return self._cluster.executable
        else:
            return Project._inferred_executables.get(suffix, '<INFER>')

    def _infer_queue(self) -> Literal['default', 'largeq', 'testq', 'gpuq']:
        # TODO: write conditions under which this returns testq/gpuq
        q = self.config.pbs_params.queue
        if q == '<INFER>':
            # Dartmouth Discovery cluster policy: batches of >600 jobs
            # should be submitted to largeq
            # PyCharm bug: Literals aren't detected in ternaries
            # noinspection PyTypeChecker
            return 'largeq' if len(self.jobs) > 600 else 'default'
        return q

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

    ####################################################################
    #                          PUBLIC METHODS                          #
    ####################################################################
    def configure(self, **config_options):
        # ADD DOCSTRING - updates self.config, accepts fields names as
        #  args & updates fields to values passed to them
        self.config.update(**config_options)
        pass

    def check_submittable(self) -> bool:
        # ADD DOCSTRING
        # returns True if all requirements to submit jobs are met
        # TODO: add check for whether or not self.pre_submit, jobs, and
        #  self.collector .expects_args
        # TODO: require explicitly passing email address(es) for
        #  'all_submitted', 'job_failed' notification options
        # TODO: raise error if queue is default and > 600 jobs
        if self.job_script is None:
            raise ClusterToolsProjectError(
                "No job script specified. Set 'project.job_script' to the path "
                "to the file you want to use to run individual jobs."
            )
        elif self.job_params is None and self.job_script.expects_args:
            raise ProjectConfigurationError(
                "Failed to assemble jobs for submission: job scripts appear to "
                "expect command line arguments and no job parameters were "
                "provided. Please use 'project.parametrize_jobs()' or set "
                "'project.job_params' and 'project.params_as_matrix' to "
                "provide parameters for each job"
            )
        elif (self.config.monitoring.auto_resubmit_jobs
              and not self.config.monitoring.auto_monitor_jobs):
            raise ProjectConfigurationError(
                "Auto job monitoring must be enabled to automatically resubmit "
                "aborted jobs. Please set 'project.auto_monitor_jobs = True' "
                "to enable auto monitoring, or 'project.auto_resubmit = False' "
                "to disable auto resubmission"
            )
        elif (bool(self.config.runtime_environment.env_activate_cmd)
              is not bool(self.config.runtime_environment.env_deactivate_cmd)):
            raise ProjectConfigurationError(
                "If running jobs inside a virtual environment, you must "
                "provide both a command to activate/enter the environment and "
                "a command to deactivate/exit it afterward"
            )
        elif self.config.general.job_executable == '<INFER>':
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

