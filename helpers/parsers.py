from configparser import ConfigParser

def parse_config(config_path):
    raw_config = ConfigParser(inline_comment_prefixes='#')
    with open(config_path, 'r') as f:
        raw_config.read_file(f)

    config = dict(raw_config['CONFIG'])
    config['confirm_overwrite_on_upload'] = raw_config.getboolean('CONFIG', 'confirm_overwrite_on_upload')
    return config
