import os
from os.path import dirname, realpath, join as opj
from spurplus import connect_with_retries
from .upload_scripts import upload_scripts
from ._helpers import attempt_load_config, parse_config
from .cluster_scripts.config import job_config


def remote_submit(config_path=None, sync_changes=False, await_output=False):
    """
    main function that handles submitting jobs on the cluster from your local
    machine

    :param config_path: (str, optional, default: None) path to your config file.
    If you created your config following the instructions in
    configs/template_config.txt, you can simply leave this empty
    :param sync_changes: (bool, default: False) if True, upload any local
    changes to cluster scripts before submitting jobs
    :param await_output: (bool, default: False) if True, keep the connection with
    the remote open until your submit script is finished creating jobs.
    Otherwise, terminate the connection after callin the submit script and allow
    job submission to happen in the background.
    WARNING: This can be rather lengthy process depending on the number of jobs
    you're running. Setting this to True opens you up to the possibility that
    the ssh connection may fail before job submission is finished
    :return: None (other than some hopefully some results, eventually!)
    """
    if config_path is None:
        config = attempt_load_config()
    else:
        config = parse_config(config_path)

    hostname = config['hostname']
    username = config['username']
    password = config['password']
    confirm_overwrite = config['confirm_overwrite_on_upload']

    modules = job_config['modules']
    env_type = job_config['env_type']
    env_name = job_config['env_name']
    submit_cmd_wrapper = job_config['cmd_wrapper']
    # TODO: ability to handle custom-named submission script
    submit_script_path = opj(job_config['workingdir'], 'submit.py')

    # pre-submission commands to be concatenated and run together in remote shell
    remote_cmds = ['sh', '-c']
    # command for loading module(s)
    module_load_cmd = f'module load {modules}'
    # command activating virtual environment
    if env_type == 'conda':
        activate_cmd = 'source activate'
    else:
        # TODO: add commands for venv & virtualenv activation
        raise ValueError("Only conda environments are currently supported")
    env_activate_cmd = f'{activate_cmd} {env_name}'
    # command for calling submit script
    submit_cmd = f'{submit_cmd_wrapper} {submit_script_path}'

    full_submission_cmd = ' && '.join([
        module_load_cmd,
        env_activate_cmd,
        submit_cmd
    ])

    remote_cmds.append(full_submission_cmd)




    with connect_with_retries(
            hostname=hostname,
            username=username,
            password=password
    ) as cluster:
        if sync_changes:
            script_dir = opj(dirname(realpath(__file__)), 'cluster_scripts')
            upload_scripts(
                cluster,
                script_dir,
                job_config,
                confirm_overwrite=confirm_overwrite
            )

        if await_output:
            output = cluster.check_output(remote_cmds)
            print(output)
        else:
            cluster.run(remote_cmds)
