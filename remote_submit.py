from argparse import ArgumentParser
from os.path import dirname, realpath, join as opj
from spurplus import connect_with_retries
from .upload_scripts import upload_scripts
from ._helpers import (
                        attempt_load_config,
                        fmt_remote_commands,
                        parse_config,
                        write_remote_submitter
                    )
from .cluster_scripts.config import job_config


def remote_submit(sync_changes=False, config_path=None):
    """
    main function that handles submitting jobs on the cluster from your local
    machine

    :param sync_changes: (bool, default: False) if True, upload any local
    changes to cluster scripts before submitting jobs
    :param config_path: (str, optional, default: None) path to your config file.
    If you created your config following the instructions in
    configs/template_config.txt, you can simply leave this empty
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
    job_cmd = config['submit_command']
    confirm_overwrite = config['confirm_overwrite_on_upload']

    # set commands
    if job_config['env_type'] == 'conda':
        activate_cmd = 'source activate'
        deactivate_cmd = 'conda deactivate'
    else:
        # TODO: add commands for venv & virtualenv activation
        raise ValueError("Only conda environments are currently supported")

    with connect_with_retries(
                            hostname=hostname,
                            username=username,
                            password=password
                            ) as cluster:
        if sync_changes:
            # upload cluster scripts to remote
            script_dir = opj(dirname(realpath(__file__)), 'cluster_scripts')
            upload_scripts(cluster, script_dir, job_config, confirm_overwrite)

        # create bash script to submit jobs from compute node
        submitter_filepath = write_remote_submitter(
                                                    cluster,
                                                    job_config,
                                                    activate_cmd,
                                                    deactivate_cmd
                                                    )

        # format commands for remote shell
        submitter_cmds = [job_cmd, submitter_filepath]
        remote_command = fmt_remote_commands(submitter_cmds)
        # run the submitter script
        cluster.run(remote_command)



if __name__ == '__main__':
    description = "Submit jobs to run on Dartmouth's high-performance computing\
     cluster from your local machine"
    arg_parser = ArgumentParser(description=description)
    arg_parser.add_argument(
        "--sync-changes",
        action='store_true',
        help="Update remote files with local changes before submitting"
    )
    arg_parser.add_argument(
        "--config-path",
        default=None,
        type=str,
        help="Path to your config file (optional unless you've moved your \
        config file)"
    )

    args = arg_parser.parse_args()
    remote_submit(args.sync_changes, args.config_path)
