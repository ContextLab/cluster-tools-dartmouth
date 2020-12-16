from string import Template



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
