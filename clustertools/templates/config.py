########################################
#       DO NOT MODIFY THIS FILE        #
########################################
# This file exists to make various options from project_config.ini available to
# cruncher scripts at runtime. All options should be set there rather
# than in this file.

from configparser import ConfigParser
from pathlib import Path


config_path = Path(__file__).resolve().parent.joinpath('project_config.ini')

job_config = ConfigParser()
with config_path.open() as f:
    job_config.read_file(f)



# job_config['datadir'] = opj(job_config['startir'], 'data')
# job_config['workingdir'] = opj(job_config['startir'], 'scripts')
# job_config['scriptdir'] = opj(job_config['workingdir'], 'scripts')
# job_config['lockdir'] = opj(job_config['workingdir'], 'locks')
