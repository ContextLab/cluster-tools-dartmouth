import os
from os.path import dirname, realpath, join as opj
from spurplus import connect_with_retries
from .upload_scripts import upload_scripts
from ._helpers import attempt_load_config
from .cluster_scripts.config import job_config


def remote_submit(config_path=None, sync_changes=False, view_output=False):
    """
    main function that handles submitting jobs on the cluster from your local
    machine

    :param config_path: (str, optional, default: None) path to your config file.
    If you created your config following the instructions in
    configs/template_config.txt, you can simply leave this empty
    :param sync_changes: (bool, default: False) if True, upload any local
    changes to cluster scripts before submitting jobs
    :param view_output: (bool, default: False) if True, keep the connection with
    the remote open until your submit script is finished creating jobs.
    Otherwise, terminate the connection after callin the submit script and allow
    job submission to happen in the background.
    WARNING: This can be rather lengthy process depending on the number of jobs
    you're running. Setting this to True opens you up to the possibility that
    the ssh connection may fail before job submission is finished
    :return: None (other than some hopefully some results, eventually!)
    """
    config = attempt_load_config()
    hostname = config['hostname']
    username = config['username']
    password = config['password']

    modules = job_config['modules']
    submit_cmd = job_config['cmd_wrapper']


    confirm_overwrite = config['confirm_overwrite_on_upload']

    script_dir = opj(dirname(realpath(__file__)), 'cluster_scripts')


    with connect_with_retries(
            hostname=hostname,
            username=username,
            password=password
    ) as cluster:
        if sync_changes:
            upload_scripts(
                cluster,
                script_dir,
                job_config,
                confirm_overwrite=confirm_overwrite
            )

