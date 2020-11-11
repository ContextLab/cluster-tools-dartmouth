import os
from os.path import dirname, realpath, join as opj
from spurplus import connect_with_retries
from clustertools._extras.helpers import md5_checksum, attempt_load_config, prompt_input
from .cluster_scripts.config import job_config


def upload_scripts(remote_shell, local_script_dir, job_conf, confirm_overwrite=True):
    remote_startdir = job_conf['startdir']
    remote_workingdir = job_conf['workingdir']
    remote_datadir = job_conf['datadir']

    to_upload = os.listdir(local_script_dir)
    # ignore hidden files (e.g., .DS_Store on MacOS)
    to_upload = [f for f in to_upload if not f.startswith('.')]
    for remote_dir in [remote_startdir, remote_workingdir, remote_datadir]:
        try:
            remote_shell.is_dir(remote_dir)
        except FileNotFoundError:
            # is_dir method raises exception if path doesn't exist
            print(f'creating remote directory: {remote_dir}')
            remote_shell.mkdir(remote_dir)

    print("uploading scripts...")
    for file in to_upload:
        src_path = opj(local_script_dir, file)
        dest_path = opj(remote_workingdir, file)
        if remote_shell.exists(dest_path):
            # don't bother uploading file if it hasn't been edited
            local_checksum = md5_checksum(src_path)
            remote_checksum = remote_shell.md5(dest_path)
            if local_checksum == remote_checksum:
                print(f"skipping {file} (no changes)")
                continue

            if confirm_overwrite:
                # prompt for confirmation of overwrite if option is enabled
                question = f"{file}: overwrite remote version with local changes?"
                overwrite_confirmed = prompt_input(question)
                if not overwrite_confirmed:
                    print(f"skipping {file} (overwrite declined)")
                    continue

        remote_shell.put(src_path, dest_path, create_directories=False)
        print(f"uploaded {file}")
    print("finished uploading scripts")


# setup for running as a stand-alone script
if __name__ == '__main__':
    config = attempt_load_config()
    hostname = config['hostname']
    username = config['username']
    password = config['password']
    confirm_overwrite = config['confirm_overwrite_on_upload']

    script_dir = opj(dirname(realpath(__file__)), 'cluster_scripts')

    with connect_with_retries(
        hostname=hostname,
        username=username,
        password=password
    ) as cluster:
        upload_scripts(
            cluster,
            script_dir,
            job_config,
            confirm_overwrite=confirm_overwrite
        )
