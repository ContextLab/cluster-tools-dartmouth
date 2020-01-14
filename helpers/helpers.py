import sys
from configparser import ConfigParser

def parse_config(config_path):
    """
    parses various user-specifc options from config file in configs dir
    """
    raw_config = ConfigParser(inline_comment_prefixes='#')
    with open(config_path, 'r') as f:
        raw_config.read_file(f)

    config = dict(raw_config['CONFIG'])
    config['confirm_overwrite_on_upload'] = raw_config.getboolean('CONFIG', 'confirm_overwrite_on_upload')
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
