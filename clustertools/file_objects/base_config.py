from configparser import ConfigParser
from typing import Dict, Optional, Union

from clustertools.cluster import Cluster
from clustertools.file_objects.tracked_attr_config import AttributeConfig
from clustertools.file_objects.synced_file import SyncedFile
from clustertools.shared.environ import MonitoredEnviron
from clustertools.shared.typing import PathLike


class BaseConfig(SyncedFile):
    # ADD DOCSTRING
    @staticmethod
    def _environ_to_str(environ: Union[MonitoredEnviron, Dict[str, str]]) -> str:
        str_fmt = '\n'.join(' = '.join(item) for item in environ.items())
        if str_fmt != '':
            str_fmt = '\n' + str_fmt
        return str_fmt

    @staticmethod
    def _type_to_str(key: str, value: Union[str, bool, int, AttributeConfig]) -> str:
        if value is True or value is False:
            return str(value).lower()
        elif isinstance(value, int):
            return str(value)
        elif key == 'environ':
            return BaseConfig._environ_to_str(value)
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
        self._environ_update_hook = None

    def __getattr__(self, item):
        # makes AttributeConfig methods and fields accessible directly
        # on this object, rather than via the object's ._config attr
        try:
            return getattr(self._config, item)
        except KeyError:
            raise AttributeError(f"'{self.__class__.__name__}' as no "
                                 f"attribute '{item}'") from None

    def __getitem__(self, item):
        # makes config options/values accessible via my_config[option]
        # rather than my_config._config[option]
        return self._config[item]

    def __setattr__(self, name, value):
        # makes top-level AttributeConfig fields settable directly on
        # this object. Does attribute lookup via self.__dict__ to avoid
        # recusrive interaction with getattr() call in self.__getattr__
        _d = self.__dict__
        if name not in _d and '_config' in _d and name in _d['_config']:
            self._config.__setattr__(name, value)
        else:
            super().__setattr__(name, value)

    def __setitem__(self, key, value):
        # makes the object support item assignment, but only for fields
        # in self._config
        self._config[key] = value

    def _config_update_hook(self) -> None:
        # TODO: rework how the hook is called and what args are passed
        #  in AttributeConfig so that you have access to the key and
        #  value inside this function and can just update one field of
        #  self._configparser rather than the whole thing every time
        for sec_name, section in self._configparser.items():
            if sec_name == 'DEFAULT':
                continue
            elif '.' in sec_name:
                conf_sec, conf_subsec = sec_name.split('.')
                conf_section = self._config[conf_sec][conf_subsec]
            else:
                conf_sec = sec_name
                conf_section = self._config[conf_sec]
            for option, value in section.items():
                section[option] = self._type_to_str(option, conf_section[option])
        self.write_config_file()

    def _init_local(self):
        # NOTE: currently super()._init_local() just 'pass'es. If that
        # changes, this should call it.
        self._configparser = self._load_configparser()
        self._config = self._parse_config()

    def _init_remote(self):
        if not self._cluster.is_dir(self.remote_path.parent):
            self._cluster.mkdir(self.remote_path.parent)
        super()._init_remote()

    def _load_configparser(self) -> ConfigParser:
        # the ConfigParser object is stored so it can be used to write to the file
        parser = ConfigParser(strict=True)
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
        return AttributeConfig(config, update_hook=self._config_update_hook)

    def _str_to_environ(self, environ_str: str) -> MonitoredEnviron:
        keys_vals = map(lambda x: x.split('='), environ_str.strip().splitlines())
        env_dict = {k.strip(): v.strip() for k, v in keys_vals}
        return MonitoredEnviron(initial_env=dict(),
                                custom_vars=env_dict,
                                update_hook=self._environ_update_hook)

    def _str_to_type(self, key: str, value: str) -> Union[str, bool, int, MonitoredEnviron]:
        if value == 'true':
            return True
        elif value == 'false':
            return False
        elif value.isdigit():
            return int(value)
        elif key == 'environ':
            return self._str_to_environ(value)
        else:
            return value

    def write_config_file(self):
        # ADD DOCSTRING
        # called from inside the AttributeConfig's update hook to write
        # changes to the original file and sync with remote, if connected
        with self.local_path.open('w') as f:
            self._configparser.write(f, space_around_delimiters=True)
        if self._cluster.connected:
            self.upload()