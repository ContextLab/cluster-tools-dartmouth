from __future__ import annotations


from string import Template
from typing import List, Literal, Optional, Sequence, Tuple, TYPE_CHECKING

if TYPE_CHECKING:
    from clustertools.file_objects.project_script import ProjectScript
    from clustertools.project.project import Project


class Job:
    # ADD DOCSTRING
    _wrapper_template = Template(
        """#!/bin/bash -l
        #${directive_prefix} -N ${job_name}
        #${directive_prefix} -d ${project_root}
        #${directive_prefix} -w ${project_root}
        #${directive_prefix} -o ${stdout_path}
        #${directive_prefix} -e ${stderr_path}
        #${directive_prefix} -q ${queue}
        #${directive_prefix} -l nodes=${n_nodes}:ppn=${ppn}
        #${directive_prefix} -l walltime=${wall_time}
        #${directive_prefix} -m ${mail_options}
        ${email_directive}
        ${dependency_directive}
        ${hold_directive}
        ${environ_export_directive}

        echo "${job_type} running on:"
        echo "host: $PBS_O_HOST"
        echo "server: $PBS_SERVER"

        ${module_load_cmd}
        ${env_activate_cmd}

        echo "${job_type} script started at `date`"

        ${job_executable} ${job_script_path} ${job_params}

        echo "${job_type} script finished at `date`"
        ${env_deactivate_cmd}
        """
    )

    def __init__(
            self,
            project: Project,
            script: ProjectScript,
            kind: Literal['pre_submit', 'submitter', 'runner', 'collector', 'monitor'],
            params: Optional[Sequence] = None
    ) -> None:
        # ADD DOCSTRING
        # status key:
        #   C - completed
        #   H - held
        #   N - not submitted
        #   Q - queued
        #   R - running
        #   W - waiting
        self._project = project
        self.script = script
        self.kind = kind
        self.params = params
        if self.params is not None:
            self.name = f'{self.kind}_{"_".join(self.params)}'
        else:
            self.name = self.kind
        self.stdout_path = self._project.stdout_dir.joinpath(f'{self.name}.stdout')
        self.stderr_path = self._project.stderr_dir.joinpath(f'{self.name}.stderr')
        self.wrapper_path = self._project.wrapper_dir.joinpath(f'{self.name}.sh')
        self.status: Literal['C', 'H', 'N', 'Q', 'R', 'W'] = 'N'
        # not assigned until submission
        self.jobid: Optional[int] = None

    @property
    def stdout(self):
        if self.status in ('N', 'Q', 'W'):
            raise AttributeError(
                f"stdout is not available for job '{self.name}'. The job has "
                "not started running yet."
            )
        return self._project._cluster.read_text(path=self.stdout_path, encoding='utf-8')

    @property
    def stderr(self):
        if self.status in ('N', 'Q', 'W'):
            raise AttributeError(
                f"stdout is not available for job '{self.name}'. The job has "
                "not started running yet."
            )
        return self._project._cluster.read_text(path=self.stderr_path, encoding='utf-8')

    @property
    def wrapper_template(self):
        return '\n'.join(map(str.lstrip, Job._wrapper_template.template.splitlines()))

    @property
    def wrapper(self):
        proj = self._project
        # first, fill in fields whose values:
        #   A) in turn contain configurable fields, or
        #   B) depend on the job type
        # NOTE: logic is written to minimize duplicate conditional
        # checks and namespace lookups run by the interpreter at the
        # expense of including duplicate LOC
        field_vals = dict()
        proj_environ = proj.environ
        if any(proj_environ):
            environ_fmt = ','.join('='.join(item) for item in proj_environ.items()),
            # if set, environment variables are exported to all job types
            field_vals['environ_export_directive'] = ('#${directive_prefix} -v '
                                                      f'{environ_fmt}')
        else:
            field_vals['environ_export_directive'] = ''
        if self.kind in ('runner', 'collector', 'pre_submit'):
            field_vals['job_executable']: proj.job_executable
            field_vals['n_nodes']: proj.n_nodes
            field_vals['ppn']: proj.ppn
            field_vals['wall_time']: proj.wall_time
            modules = ' '.join(proj.modules)
            field_vals['dependency_directive'] = ''
            if any(modules):
                cmd = f"""echo "loading modules: {modules}" 
                          module load ${modules}
                       """.splitlines()
                field_vals['module_load_cmd'] = '\n'.join(map(str.lstrip, cmd))
            else:
                field_vals['module_load_cmd'] = ''
            if self.kind == 'collector':
                field_vals['hold_directive'] = '#${directive_prefix} -h'
            else:
                field_vals['hold_directive'] = ''
        else:
            # TODO: find a cleaner way of doing this so the loaded
            #  module becomes the default 'python'. Will need to account
            #  for users who have a Python executable assigned in their
            #  dotfiles or an old-style conda executable that writes
            #  conda_init to $HOME/.bashrc
            field_vals['job_executable'] = 'python3.7'
            field_vals['n_nodes'] = 1
            field_vals['ppn'] = 1
            field_vals['hold_directive'] = ''
            # TODO: this is currently Dartmouth/Discovery-specific.
            module_cmd = """echo "loading modules: python/3.7-Anaconda
                            module load python/3.7-Anaconda
                         """.splitlines()
            field_vals['module_load_cmd'] = '\n'.join(map(str.lstrip, module_cmd))
            if self.kind == 'submitter':
                # estimate walltime needed to submit all jobs, assuming
                # (conservatively) 1 job submitted every 5s plus some
                # overhead for module load, conda activate, etc.
                total_secs = len(proj.jobs) * 5 + 60
                hrs = total_secs // 3600
                mins = total_secs % 3600 // 60
                secs = total_secs % 3600 % 60
                field_vals['wall_time'] = f'{hrs:02d}:{mins:02d}:{secs:02d}'
                if proj.notify_all_submitted:
                    field_vals['mail_options'] = ''
                if proj.pre_submit_script is not None:
                    field_vals['dependency_directive'] = ('#${directive_prefix} '
                                                          '-W depend=afterok:$1')

            else:
                # self.kind == 'monitor'
                # estimate walltime based on jobs' walltime, given that
                # not all start from the queue at the same time (up to
                # 1 day max)




        # TODO: make sure this checks for proper values in final field format
        email_addrs = self._project.config.notifications.email_list
        if field_vals['mail_options'] == 'n' or self._project.email_list == 'INFER':
            # emails will be sent to default email address for submitting user
            field_vals['email_directive'] = ''
        else:
            field_vals['email_directive'] = '#${directive_prefix} -M ${user}'
        # substitute and convert back to template
        partial_wrapper = Job._wrapper_template.safe_substitute(field_vals)
        partial_template = Template(partial_wrapper)
        # then fill in remaining fields
        field_vals = {
            'directive_prefix': proj.directive_prefix,
            'job_name': self.name,
            'project_root': proj.root_dir,
            'stdout_path': self.stdout_path,
            'stderr_path': self.stderr_path,
            'queue': proj.queue,
            'user': proj.user_to_notify,

        }







        if any(proj_environ):
            environ_fmt = ','.join('='.join(item) for item in proj_environ.items()),
            # if set, environment variables are exported to all job types
            field_vals['environ_export_directive'] = ('#${directive_prefix} -v '
                                                      f'{environ_fmt}')
        else:
            field_vals['environ_export_directive'] = ''
        if self.kind == 'runner':
            field_vals['job_executable']: proj.job_executable
            field_vals['n_nodes']: proj.n_nodes
            field_vals['ppn']: proj.ppn
            field_vals['wall_time']: proj.wall_time
            field_vals['dependency_directive'] = ''
            field_vals['hold_directive'] = ''
            modules = ' '.join(proj.modules)
            if any(modules):
                cmd = f"""echo "loading modules: {modules}"
                module load ${modules}
                """.splitlines()
                field_vals['module_load_cmd'] = '\n'.join(map(str.lstrip, cmd))
            else:
                field_vals['module_load_cmd'] = ''
        elif self.kind == 'submitter':
            field_vals['job_executable'] = 'python'
            field_vals['n_nodes'] = 1
            field_vals['ppn'] = 1
            # estimate walltime needed to submit all jobs, assuming
            # (conservatively) 1 job submitted every 3s plus some
            # overhead for module load, conda activate, etc.
            total_secs = len(proj.jobs) * 3 + 30
            hrs = total_secs // 3600
            mins = total_secs % 3600 // 60
            secs = total_secs % 3600 % 60
            field_vals['wall_time'] = f'{hrs:02d}:{mins:02d}:{secs:02d}'
            field_vals['hold_directive'] = ''
            if proj.pre_submit_script is not None:
                # submit script will receive pre-submit job's jobid ("$1")
                field_vals['dependency_directive'] = '#${directive_prefix} -W depend=afterok:$1'
            else:
                field_vals['dependency_directive'] = ''
            field_vals['hold_directive'] = ''
            field_vals['module_load_cmd'] = ''
        elif self.kind == 'monitor':
            ...
        if self.kind == 'collector':
            field_vals['hold_directive'] = '#${directive_prefix} -h'
        else:
            field_vals['hold_directive'] = ''

        # TODO: make sure the spacing/alignment of these multiline
        #  strings is getting translated properly
        full_wrapper_str = Job._wrapper_template.safe_substitute(first_subs)
        full_wrapper_template = Template(full_wrapper_str)
        # fill in remaining fields
        field_vals = {
            'directive_prefix': proj.directive_prefix,
            'job_name': self.name,
            'project_root': proj.root_dir,
            'stdout_path': self.stdout_path,
            'stderr_path': self.stderr_path,
            'queue': proj.queue,
            'user': proj.user_to_notify,
            'job_type': self.kind,
            'modules': ' '.join(proj.modules)
        }
        # logic for constructing #PBS -m option str based on project
        # config values and job type
        # this could be written in fewer lines, but this way results in
        # fewer namespace lookups, which could potentially add up to
        # something significant for extremely long JobLists
        # NOTE: the 'all_finished' config field affects params passed to monitor job, rather than
        mail_opts = ''
        if self.kind == 'submitter' and proj.notify_all_submitted:
            mail_opts = 'e'
        elif self.kind == 'collector' and proj.notify_collector_finished:
            mail_opts = 'e'
        elif self.kind == 'runner':
            if proj.notify_job_started:
                mail_opts += 'b'
            if proj.notify_job_finished:
                mail_opts += 'e'
            if proj.notify_job_aborted:
                mail_opts += 'a'
            if proj.notify_job_failed:
                mail_opts += 'f'
        if mail_opts == '':
            # no mail will be sent
            mail_opts = 'n'
        field_vals['mail_options'] = mail_opts
        # only have to check one of the two virtual environment commands,
        # 'Project.check_submittable()' ensures either both or neither
        # is set
        if proj.env_activate_cmd:
            a_cmd = f"""echo "activating environment
                    {proj.env_activate_cmd}
                    """
            d_cmd = f"""
                    echo "deactivating environment"
                    {proj.env_deactivate_cmd}"""
            a_cmd_fmt = '\n'.join(map(str.lstrip, a_cmd.splitlines()))
            d_cmd_fmt = '\n'.join(map(str.lstrip, d_cmd.splitlines()))
            field_vals['env_activate_cmd'] = a_cmd_fmt
            field_vals['env_deactivate_cmd'] = d_cmd_fmt
        else:
            field_vals['env_activate_cmd'] = ''
            field_vals['env_deactivate_cmd'] = ''
        return full_wrapper_template.substitute(field_vals)

    # @property
    # def wrapper(self):
    #     proj = self._project
    #     # first, fill in fields whose values contain configurable fields
    #     subtemplates = dict()
    #     if proj.pre_submit_script is not None and self.kind == 'submitter':
    #         # jobid of pre_submit job will get passed to submit script ("$1")
    #         subtemplates['dependency_directive'] = '#${directive_prefix} -W depend=afterok:$1'
    #     else:
    #         subtemplates['dependency_directive'] = ''
    #     if self.kind == 'collector':
    #         subtemplates['hold_directive'] = '#${directive_prefix} -h'
    #     else:
    #         subtemplates['hold_directive'] = ''
    #     if any(proj.environ):
    #         subtemplates['environ_export_directive'] = '#${directive_prefix} -v ${environ_fmt}'
    #     else:
    #         subtemplates['environ_export_directive'] = ''
    #     # TODO: make sure the spacing/alignment of these multiline
    #     #  strings is getting translated properly
    #     if any(proj.modules):
    #         cmd = """echo "loading modules: ${modules}"
    #         module load ${modules}
    #         """
    #         cmd_fmt = '\n'.join(map(str.lstrip, cmd.splitlines()))
    #         subtemplates['module_load_cmd'] = cmd_fmt
    #     else:
    #         subtemplates['module_load_cmd'] = ''
    #     full_wrapper_str = Job._wrapper_template.safe_substitute(subtemplates)
    #     full_wrapper_template = Template(full_wrapper_str)
    #     # fill in remaining fields
    #     field_vals = {
    #         'directive_prefix': proj.directive_prefix,
    #         'job_name': self.name,
    #         'project_root': proj.root_dir,
    #         'stdout_path': self.stdout_path,
    #         'stderr_path': self.stderr_path,
    #         'queue': proj.queue,
    #         'n_nodes': proj.n_nodes,
    #         'ppn': proj.ppn,
    #         'wall_time': proj.wall_time,
    #         'user': proj.user_to_notify,
    #         'job_type': self.kind,
    #         'job_executable': proj.job_executable,
    #         'environ_fmt': ','.join('='.join(item) for item in proj.environ.items()),
    #         'modules': ' '.join(proj.modules)
    #     }
    #     # logic for constructing #PBS -m option str based on project
    #     # config values and job type
    #     # this could be written in fewer lines, but this way results in
    #     # fewer namespace lookups, which could potentially add up to
    #     # something significant for extremely long JobLists
    #     # NOTE: the 'all_finished' config field affects params passed to monitor job, rather than
    #     mail_opts = ''
    #     if self.kind == 'submitter' and proj.notify_all_submitted:
    #         mail_opts = 'e'
    #     elif self.kind == 'collector' and proj.notify_collector_finished:
    #         mail_opts = 'e'
    #     elif self.kind == 'runner':
    #         if proj.notify_job_started:
    #             mail_opts += 'b'
    #         if proj.notify_job_finished:
    #             mail_opts += 'e'
    #         if proj.notify_job_aborted:
    #             mail_opts += 'a'
    #         if proj.notify_job_failed:
    #             mail_opts += 'f'
    #     if mail_opts == '':
    #         # no mail will be sent
    #         mail_opts = 'n'
    #     field_vals['mail_options'] = mail_opts
    #     # only have to check one of the two virtual environment commands,
    #     # 'Project.check_submittable()' ensures either both or neither
    #     # is set
    #     if proj.env_activate_cmd:
    #         a_cmd = f"""echo "activating environment
    #                     {proj.env_activate_cmd}
    #                     """
    #         d_cmd = f"""
    #                     echo "deactivating environment"
    #                     {proj.env_deactivate_cmd}"""
    #         a_cmd_fmt = '\n'.join(map(str.lstrip, a_cmd.splitlines()))
    #         d_cmd_fmt = '\n'.join(map(str.lstrip, d_cmd.splitlines()))
    #         field_vals['env_activate_cmd'] = a_cmd_fmt
    #         field_vals['env_deactivate_cmd'] = d_cmd_fmt
    #     else:
    #         field_vals['env_activate_cmd'] = ''
    #         field_vals['env_deactivate_cmd'] = ''
    #     return full_wrapper_template.substitute(field_vals)


class JobListCache(dict):
    # ADD DOCSTRING
    # - allows JobList to lazily construct individual Job objects as
    #   needed rather than holding a potentially enormous list of them
    #   in memory.
    # - stores jobs in a dict whose keys are job's parameters (tuples)
    #   and values are constructed Job objects
    # - __missing__ method works like collections.defaultdict if the
    #   default_factory function accepted arguments in order to store
    #   value based on the missing key. But here, first positional
    #   argument must be a Project object, rather than a callable
    def __init__(self, *args, **kwargs):
        # ADD DOCSTRING
        self._project: Project = args[0]
        super().__init__(*args[1:], **kwargs)

    def __missing__(self, key):
        self[key] = job = Job(project=self._project,
                              script=self._project.job_script,
                              kind='runner',
                              params=key)
        return job


class JobList:
    # ADD DOCSTRING
    # could inherit from collections.abc.Sequence, but would need to
    # override enough abstract methods that it's hardly worth it
    def __init__(
            self,
            project: Project,
            param_list: Optional[List[Tuple[str]]] = None,
            cache: Optional[JobListCache] = None
    ):
        # ADD DOCSTRING
        self._project = project
        self._param_list = param_list
        if cache is not None:
            self._cache = cache
        else:
            self._cache = JobListCache(project)

    def __contains__(self, job: Job) -> bool:
        try:
            return job.params in self._job_params
        except TypeError:
            # project's job_params attr has not been set yet
            if self._project.job_params is None:
                return False
            raise

    def __delitem__(self, ix):
        # NOTE: deleting job from JobList deletes also deletes
        # corresponding entry in project's job_params list
        if self._param_list is None:
            # full JobList
            del self._project._job_params[ix]
        else:
            # slice of full JobList
            del self._param_list[ix]
        try:
            # remove Job from cache, if it exists
            del self._cache[ix]
        except KeyError:
            pass



    def __getitem__(self, ix):
        # don't need to handle case where project's job params aren't
        # set, exception raised makes sufficient sense
        if isinstance(ix, slice):
            param_list = self._job_params[ix]
            return JobList(project=self._project,
                           param_list=param_list,
                           cache=self._cache)
        return self._cache[self._job_params[ix]]

    def __iter__(self):
        try:
            for i in iter(self._job_params):
                yield self._cache[i]
        except TypeError:
            # project's job_params attr has not been set yet
            if self._param_list is None:
                pass

    def __len__(self):
        try:
            return len(self._job_params)
        except TypeError:
            # project's job_params attr has not been set yet
            if self._project.job_params is None:
                return 0
            raise

    def __repr__(self):
        return f"<JobList: proxied list of {len(self)} Job objects>"

    def __reversed__(self):
        try:
            for i in reversed(self._job_params):
                yield self._cache[i]
        except TypeError:
            # project's job_params attr has not been set yet
            if self._project.job_params is None:
                pass

    @property
    def _job_params(self) -> Optional[List[Tuple[str]]]:
        # list of job parameters is accessed via property in order to
        # enable efficient slicing behavior. Slicing a JobList yields a
        # new JobList object for the corresponding indices of
        # self._project.job_params, rather than constructing a Job
        # object for each index of the slice and returning a list. For
        # the full JobList object, self._param_list is None and
        # self.job_params references the project's param list so that
        # any changes made to the job params are reflected in the Job
        # objects. For slices, self._param_list is the corresponding
        # slice of self._project.job_params so that the indices of the
        # two align. As with regular lists, mutating slices does not
        # mutate the full list. Slices inherit the full JobList's cache,
        # but Job objects constructed when indexing the slice are not
        # added to the full JobList's cache.
        if self._param_list is not None:
            return self._param_list
        return self._project.job_params

    def clear_cache(self):
        # ADD DOCSTRING
        # cache of constructed Job objects gets cleared when
        # self._project.job_script or self._project.job_params are
        # updated
        self._cache = JobListCache(self._project)

    def copy(self):
        # ADD DOCSTRING - return a shallow copy of the JobList
        # implemented so JobList supports expected 'list' functionality.
        # returns a slice containing all jobs
        return self[:]

    def pop(self, index=-1):
        # ADD DOCSTRING
        # no way (that isn't totally janky) to enforce positional-only
        # arg pre-Python 3.8
        if self._param_list is None:
            # full JobList
            params = self._project._job_params.pop(index)
        else:
            # slice of full JobList
            params = self._param_list.pop(index)
        try:
            # if Job is cached, just pop that and return it
            return self._cache.pop(params)
        except KeyError:
            return Job(project=self._project,
                       script=self._project.job_script,
                       kind='runner',
                       params=params)
