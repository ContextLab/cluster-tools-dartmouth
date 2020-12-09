from configparser import ConfigParser
from typing import Dict, Optional, Union

from clustertools.cluster import Cluster
from clustertools.file_objects.attibute_config import AttributeConfig
from clustertools.file_objects.synced_file import SyncedFile
from clustertools.shared.typing import PathLike


class BaseConfig(SyncedFile):
    # ADD DOCSTRING
    # @staticmethod
    # def _getdict(val):
    #     """
    #     splits a newline separated list of values for a single option (where
    #     each option takes the format `sub-option = sub-value`) into a
    #     dictionary with the format `{sub-option: sub-value}`
    #     """
    #     keys_vals = map(lambda x: x.split('='), val.strip().splitlines()[1:])
    #     return {k.strip(): v.strip() for k, v in keys_vals}
    #
    # @staticmethod
    # def _getboolean(val):
    #     # equivalent to ConfigParser.getboolean
    #     _val = val.lower()
    #     if _val not in ConfigParser.BOOLEAN_STATES:
    #         raise ValueError(f'Not a boolean: {val}')
    #     return ConfigParser.BOOLEAN_STATES[_val]
    #
    # TYPE_CONVERTERS = {'dict': _getdict, 'boolean': _getboolean, 'int': int, 'float': float}
    # FIELD_TYPES = ()

    @staticmethod
    def _str_to_type(key: str, value: str) -> Union[str, bool, int, Dict[str, str]]:
        if value == 'true':
            return True
        elif value == 'false':
            return False
        elif value.isdigit():
            return int(value)
        elif key == 'environ':
            keys_vals = map(lambda x: x.split('='), value.strip().splitlines()[1:])
            return {k.strip(): v.strip() for k, v in keys_vals}
        else:
            return value

    def __init__(
            self,
            cluster: Cluster,
            local_path: PathLike,
            remote_path: Optional[PathLike] = None
    ) -> None:
        # ADD DOCSTRING
        super().__init__(cluster=cluster, local_path=local_path, remote_path=remote_path)
        self._configparser = self._load_configparser()
        self._config = self._parse_config()

    def _init_remote(self):
        if not self._cluster.is_dir(self.remote_path.parent):
            self._cluster.mkdir(self.remote_path.parent)
        super()._init_remote()

    def _load_configparser(self) -> ConfigParser:
        # the ConfigParser object is stored so it can be used to write to the file
        parser = ConfigParser()
        # parser = ConfigParser(converters=BaseConfig.CONVERTERS)
        with self.local_path.open() as f:
            parser.read_file(f)
        return parser

    def _parse_config(self) -> AttributeConfig:
        config = dict()
        for sec_name, section in self._configparser.items():
            if sec_name == 'DEFAULT':
                continue
            section_dict = dict()
            for option, value in section.items():
                section_dict[option] = self._str_to_type(option, value)
            if '.' in sec_name:
                sec_name, subsec_name = sec_name.split('.')
                config[sec_name][subsec_name] = section_dict
            else:
                config[sec_name] = section_dict
        return AttributeConfig(config)
