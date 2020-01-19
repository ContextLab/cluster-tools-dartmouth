from argparse import ArgumentParser
from os.path import dirname, realpath, join as opj
from spurplus import connect_with_retries
from .upload_scripts import upload_scripts
from ._helpers import attempt_load_config, fmt_remote_commands, parse_config
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
    Otherwise, terminate the connection after calling the submit script and allow
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

    env_type = job_config['env_type']
    env_name = job_config['env_name']
    submit_cmd_wrapper = job_config['cmd_wrapper']
    # TODO: ability to handle custom-named submission script
    submit_script_path = opj(job_config['workingdir'], 'submit.py')

    # load python module
    module_load_cmd = f'module load python'
    # activate environment
    if env_type == 'conda':
        activate_cmd = 'source activate'
    else:
        # TODO: add commands for venv & virtualenv activation
        raise ValueError("Only conda environments are currently supported")
    env_activate_cmd = f'{activate_cmd} {env_name}'
    # command for calling submit script
    submit_cmd = f'{submit_cmd_wrapper} {submit_script_path}'

    full_submission_cmd = [
        module_load_cmd,
        env_activate_cmd,
        submit_cmd
    ]
    remote_command = fmt_remote_commands(full_submission_cmd)

    with connect_with_retries(
            hostname=hostname,
            username=username,
            password=password
    ) as cluster:
        if sync_changes:
            script_dir = opj(dirname(realpath(__file__)), 'cluster_scripts')
            upload_scripts(cluster, script_dir, job_config, confirm_overwrite)

        if await_output:
            output = cluster.check_output(remote_command)
            print(output)
        else:
            cluster.run(remote_command)


if __name__ == '__main__':
    description = "Submit jobs to run on Dartmouth's high-performance computing\
     cluster from your local machine"
    arg_parser = ArgumentParser(description=description)
    arg_parser.add_argument(
        "--config-path",
        default=None,
        type=str,
        help="Path to your config file"
    )
    arg_parser.add_argument(
        "--sync-changes",
        action='store_true',
        help="Update remote files with local changes before submitting"
    )
    arg_parser.add_argument(
        "--await-output",
        action='store_true',
        help="Keep the connection with the remote server open until job \
        submission has finished (This can be a very longtime !)"
    )

    args = arg_parser.parse_args()
    remote_submit(args.config_path, args.sync_changes, args.await_output)