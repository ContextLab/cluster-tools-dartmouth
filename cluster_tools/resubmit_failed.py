import sys
from argparse import ArgumentParser
from os.path import join as opj
from spurplus import connect_with_retries
from .cluster_scripts.config import job_config
from ._helpers import (
                        attempt_load_config,
                        fmt_remote_commands,
                        get_qstat,
                        parse_config,
                        prompt_input
                    )


def resubmit_failed(confirm_resubmission=False, config_path=None):
    # TODO: add docstring

    if config_path is None:
        config = attempt_load_config()
    else:
        config = parse_config(config_path)

    hostname = config['hostname']
    username = config['username']
    password = config['password']
    confirm = config['confirm_resubmission']

    workingdir = job_config['workingdir']
    scriptdir = job_config['scriptdir']
    job_name = job_config['jobname']

    # set confirmation option from config if not set here
    if confirm and not confirm_resubmission:
        confirm_resubmission = True

    # set submission command
    if username.startswith('f00'):
        job_cmd = 'mksub'
    else:
        job_cmd = 'qsub'

    with connect_with_retries(
            hostname=hostname,
            username=username,
            password=password
    ) as cluster:
        cluster_sftp = cluster.as_sftp()

        # get all created bash scripts
        all_scripts = cluster_sftp.listdir(scriptdir)
        print(f"found {len(all_scripts)} job scripts")

        stdout_files = [f for f in cluster_sftp.listdir(workingdir)
                        if f.startswith(f'{job_name}.o')]
        print(f"found {len(stdout_files)} job stdout files")

        # get output of qstat command
        running_jobs = [line for line in get_qstat(cluster)
                        if len(line) > 0 and line[0].isnumeric()]
        # filter out completed jobs, isolate jobid
        running_jobids = [line.split('.')[0] for line in running_jobs
                          if line.split()[-2] != 'C']
        print(f"found {len(running_jobids)} running jobs")

        print("parsing stdout files...")

        successful_jobs = {}
        for outfile in stdout_files:
            jobid = outfile.split('.o')[1]

            # read stdout file
            stdout_path = opj(workingdir, outfile)
            stdout = cluster.read_text(stdout_path)
            try:
                job_script = stdout.split('script name: ')[1].splitlines()[0]
                # track successfully finished jobs
                if 'job script finished' in stdout:
                    successful_jobs[job_script] = jobid
            except (IndexError, ValueError):
                print(
                    f"failed to find corresponding script for {outfile}..."
                    )
                continue

        to_resubmit = [s for s in all_scripts
                       if s not in list(successful_jobs.keys())]

        if confirm_resubmission:
            view_scripts = prompt_input("View jobs to be resubmitted before \
                                        proceeding?")
            if view_scripts:
                print('\n'.join(to_resubmit))
                resubmit_confirmed = prompt_input("Do you want to resubmit \
                                                    these jobs?")
                if not resubmit_confirmed:
                    sys.exit()

        print("Removing failed jobs' stdout/stderr files...")
        for outfile in stdout_files:
            jobid = outfile.split('.o')[1]
            if not (jobid in successful_jobs.values()
                    or jobid in running_jobids):
                stdout_path = opj(workingdir, outfile)
                stderr_path = opj(workingdir, f'{job_name}.e{jobid}')
                cluster.remove(stdout_path)
                cluster.remove(stderr_path)

        print(f"resubmitting {len(to_resubmit)} jobs")
        for job in to_resubmit:
            script_path = opj(scriptdir, job)
            print(f"resubmitting {job}")
            cmd = fmt_remote_commands([f'{job_cmd} {script_path}'])
            cluster.run(cmd)


if __name__ == '__main__':
    description = "Resubmit jobs identified as having failed during initial \
                    submission"
    arg_parser = ArgumentParser(description=description)
    arg_parser.add_argument(
        "-confirm",
        action='store_true',
        help="Whether or not you want to be shown the list of \
            to-be-resubmitted jobs and prompted to confirm before resubmitting \
            them.  Passing this overrides default behavior set in your config file"
    )
    arg_parser.add_argument(
        "--config-path",
        default=None,
        type=str,
        help="Path to your config file (optional unless you've moved your \
            config file)"
    )

    args = arg_parser.parse_args()
    resubmit_failed(args.confirm, args.config_path)
