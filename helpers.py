from configparser import ConfigParser

def parse_config(config_path):
    raw_config = ConfigParser(inline_comment_prefixes='#')
    with open(config_path, 'r') as f:
        raw_config.read_file(f)

    config = dict(config['CONFIG'])
    