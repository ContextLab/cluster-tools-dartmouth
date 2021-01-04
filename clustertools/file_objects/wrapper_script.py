from __future__ import annotations

from inspect import cleandoc
from string import Template
from typing import Literal, TYPE_CHECKING

if TYPE_CHECKING:
    from clustertools.project.job import Job



# TODO: look into adding #PBS -W depend=dependency_list to enforce
#  pre-submit/runner/collector start order
# TODO: look into whether #PBS -W group_list=group is required to access
#  resources available to 'group'
# TODO: look into adding option to run on nodes with particular 'feature's
WRAPPER_TEMPLATE = Template(
"""#!/bin/bash -l
#${directive_prefix} -N ${job_basename}_${job_suffix}
#${directive_prefix} -d ${project_root}
#${directive_prefix} -w ${project_root}
#${directive_prefix} -o ${stdout_dir}/${job_basename}_${job_suffix}.stdout
#${directive_prefix} -e ${stderr_dir}/${job_basename}_${job_suffix}.stderr
#${directive_prefix} -q ${queue}
#${directive_prefix} -l nodes=${n_nodes}:ppn=${ppn}
#${directive_prefix} -l walltime=${wall_time}
#${directive_prefix} -M ${user}
#${directive_prefix} -m ${mail_options}
${dependency_directive}
${hold_directive}
${environ_exporter}

echo "${job_type} running on:"
echo "host: $PBS_O_HOST"
echo "server: $PBS_SERVER"

${module_loader}
${virtual_env_activator}

echo "${job_type} script started at `date`"

${cmd_wrapper} ${job_script_path} ${job_params}

echo "${job_type} script finished at `date`"
${virtual_env_deactivator}
"""
)

JOB_SUFFIX = "${job_params}"


AFTER_JOBID_SUCCESS_DIRECTIVE = "#${directive_prefix} -W depend=afterok:$1"


USER_HOLD_DIRECTIVE = "#${directive_prefix} -h"


VAR_EXPORT_DIRECTIVE = "#${directive_prefix} -v ${environ_vars}"


MODULE_LOAD_COMMAND = """echo "loading modules: ${modules}"
module load ${modules}
"""


ENV_ACTIVATE_COMMAND = """echo "activating environment
${activate_cmd}
"""


ENV_DEACTIVATE_COMMAND = """
echo "deactivating environment"
${deactivate_cmd}"""


class WrapperScript:
    # ADD DOCSTRING

    raw_template = Template(
        """#!/bin/bash -l
        #${directive_prefix} -N ${job_name}
        #${directive_prefix} -d ${project_root}
        #${directive_prefix} -w ${project_root}
        #${directive_prefix} -o ${stdout_dir}/${job_name}.stdout
        #${directive_prefix} -e ${stderr_dir}/${job_name}.stderr
        #${directive_prefix} -q ${queue}
        #${directive_prefix} -l nodes=${n_nodes}:ppn=${ppn}
        #${directive_prefix} -l walltime=${wall_time}
        #${directive_prefix} -M ${user}
        #${directive_prefix} -m ${mail_options}
        ${hold_directive}
        ${environ_exporter}
        
        echo "${job_type} running on:"
        echo "host: $PBS_O_HOST"
        echo "server: $PBS_SERVER"
        
        ${module_loader}
        ${virtual_env_activator}
        
        echo "${job_type} script started at `date`"
        
        ${cmd_wrapper} ${job_script_path} ${job_params}
        
        echo "${job_type} script finished at `date`"
        ${virtual_env_deactivator}
        """
        )
    def __init__(self, job: Job):
        # ADD DOCSTRING
        self._job = job
        self.path = self._job._project.script_dir.joinpath(f'{self._job.name}.sh')

    def __repr__(self):
        return self.

    def (self, strict=False):
