import hashlib
import os
import sys
from os.path import isfile, realpath, join as opj, sep as pathsep
from string import Template
from configparser import ConfigParser


def attempt_load_config():
    """
    tries to load config file from expected path in instances where neither a
    filepath or dict-like object is provided
    """
    splitpath = realpath(__file__).split(pathsep)
    try:
        try:
            # get path to project root directory
            splitroot = splitpath[: splitpath.index('cluster-tools-dartmouth') + 1]
            project_root = pathsep.join(splitroot)
            config_dir = opj(project_root, 'configs')
        except ValueError as e:
            # pass exceptions onto broad outer exception for function
            raise FileNotFoundError(f"cluster-tools-dartmouth not found in path\
             {realpath(__file__)}").with_traceback(e.__traceback__)

        configs = os.listdir(config_dir)
        # filter out hidden files and the template config
        configs = [f for f in configs if not (f.startswith('template')
                                              or f.startswith('.'))
                   ]
        if len(configs) == 1:
            config_path = opj(config_dir, configs[0])
            config = parse_config(config_path)
            return config
        else:
            # fail if multiple or no config files are found
            raise FileNotFoundError(f"Unable to determine which config file to \
            read from {len(configs)} choices in {config_dir}")

    except FileNotFoundError as e:
        raise FileNotFoundError("Failed to load config file from expected \
        location").with_traceback(e.__traceback__)


def fmt_remote_commands(commands):
    """
    Formats a list of shell commands to be run in the SshShell instance.
    Necessary because underlying Python SSH client (Paramiko) won't run any
    state changes between commands.  So we run them all at once
    """
    executable = ['bash', '-c']
    commands_str = ' && '.join(commands)
    return executable + commands_str


def md5_checksum(filepath):
    """
    computes the MD5 checksum of a local file to compare against remote

    NOTE: MD5 IS CONSIDERED CRYPTOGRAPHICALLY INSECURE
    (see https://en.wikipedia.org/wiki/MD5#Security)
    However, it's still very much suitable in cases (like ours) where one
    wouldn't expect **intentional** data corruption
    """
    hash_md5 = hashlib.md5()
    with open(filepath, 'rb') as f:
        # avoid having to read the whole file into memory at once
        for chunk in iter(lambda: f.read(4096), b''):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()


def parse_config(config_path):
    """
    parses various user-specifc options from config file in configs dir
    """
    config_path = realpath(config_path)
    if not isfile(config_path):
        raise FileNotFoundError(f'Invalid path to config file: {config_path}')

    raw_config = ConfigParser(inline_comment_prefixes='#')
    with open(config_path, 'r') as f:
        raw_config.read_file(f)

    config = dict(raw_config['CONFIG'])
    config['confirm_overwrite_on_upload'] = raw_config.getboolean(
        'CONFIG', 'confirm_overwrite_on_upload'
    )
    return config


def prompt_input(question, default=None):
    """
    given a question, prompts user for command line input
    returns True for 'yes'/'y' and False for 'no'/'n' responses
    """
    assert default in ('yes', 'no', None), \
        "Default response must be either 'yes', 'no', or None"

    valid_responses = {
        'yes': True,
        'y': True,
        'no': False,
        'n': False
    }

    if default is None:
        prompt = "[y/n]"
    elif default == 'yes':
        prompt = "[Y/n]"
    else:
        prompt = "[y/N]"

    while True:
        sys.stdout.write(f"{question}\n{prompt}")
        response = input().lower()
        # if user hits return without typing, return default response
        if (default is not None) and (not response):
            return valid_responses[default]
        elif response in valid_responses:
            return valid_responses[response]
        else:
            sys.stdout.write("Please respond with either 'yes' (or 'y') \
            or 'no' (or 'n')\n")


def write_remote_submitter(remote_shell, job_config, env_activate_cmd, env_deactivate_cmd, submitter_walltime='12:00:00'):
    remote_dir = job_config['workingdir']
    # TODO: ability to handle custom-named submission script
    submitter_fpath = opj(remote_dir, 'submit_jobs.sh')

    try:
        assert remote_shell.is_dir(remote_dir)
    except AssertionError as e:
        raise ValueError(
            f"Can't create job submission script in dir: {remote_dir}. \
            Intended directory is an existing file."
        ).with_traceback(e.__traceback__)
    except FileNotFoundError as e:
        raise FileNotFoundError(
            f"Can't create job submission script in dir: {remote_dir}. \
            Intended directory does not exist."
        ).with_traceback(e.__traceback__)

    template_vals = {
        'jobname': job_config['jobname'],
        'walltime': submitter_walltime,
        'modules': job_config['modules'],
        'activate_cmd': env_activate_cmd,
        'deactivate_cmd': env_deactivate_cmd,
        'env_name': job_config['env_name'],
        'cmd_wrapper': job_config['cmd_wrapper'],
        'submitter_script': submitter_fpath
    }

    template = Template(
"""#!/bin/bash -l
        
#PBS -N ${jobname}-submitter
#PBS -q default
#PBS -l nodes=1:ppn=1
#PBS -l walltime=${walltime}
#PBS -m bea
        
module load $modules
$activate_cmd $env_name
        
$cmd_wrapper $submitter_script
        
$deactivate_cmd"""
    )

    content = template.substitute(template_vals)
    remote_shell.write_text(submitter_fpath, content)
    return submitter_fpath
