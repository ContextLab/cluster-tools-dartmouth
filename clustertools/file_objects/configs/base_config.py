from __future__ import annotations

from configparser import ConfigParser
from typing import Dict, Optional, TYPE_CHECKING, Union

from clustertools.file_objects.config_hooks import (BASE_CONFIG_UPDATE_HOOKS,
                                                    write_updated_config)
from clustertools.file_objects.tracked_attr_config import TrackedAttrConfig
from clustertools.file_objects.synced_file import SyncedFile
from clustertools.shared.object_monitors import MonitoredEnviron, MonitoredList

if TYPE_CHECKING:
    from clustertools.cluster import Cluster
    from clustertools.shared.typing import PathLike


class BaseConfig(SyncedFile):
    # ADD DOCSTRING

    @staticmethod
    def _environ_to_str(
            environ: Union[MonitoredEnviron[str, str], Dict[str, str]]
    ) -> str:
        str_fmt = '\n'.join(' = '.join(item) for item in environ.items())
        if str_fmt != '':
            str_fmt = '\n' + str_fmt
        return str_fmt

    @staticmethod
    def _type_to_str(
            key: str,
            value: Union[str, bool, int, MonitoredEnviron[str, str], MonitoredList[str]]
    ) -> str:
        if value is True or value is False:
            return str(value).lower()
        elif isinstance(value, int):
            return str(value)
        elif key == 'environ':
            return BaseConfig._environ_to_str(value)
        elif key == 'modules':
            return ', '.join(value)
        else:
            return value

    def __init__(
            self,
            cluster: Cluster,
            local_path: PathLike,
            remote_path: Optional[PathLike] = None
    ) -> None:
        # ADD DOCSTRING
        self._attr_update_hooks.update(BASE_CONFIG_UPDATE_HOOKS)
        super().__init__(cluster=cluster, local_path=local_path, remote_path=remote_path)
        self._environ_update_hook = None
        self._modules_update_hook = None

    def __getattr__(self, item):
        # makes TrackedAttrConfig methods and fields accessible directly
        # on this object, rather than via the object's ._config attr
        try:
            return getattr(self._config, item)
        except KeyError:
            raise AttributeError(
                f"'{self.__class__.__name__}' as no attribute '{item}'"
            ) from None

    def __getitem__(self, item):
        # makes config options/values accessible via my_config[option]
        # rather than my_config._config[option]
        return self._config[item]

    def __setattr__(self, name, value):
        # makes top-level TrackedAttrConfig fields settable directly on
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

    def _init_local(self):
        # NOTE: currently super()._init_local() just 'pass'es. If that
        # changes, this should call it.
        # bind hooks to config object instance
        global write_updated_config
        for field, hook in self._attr_update_hooks.items():
            self._attr_update_hooks[field] = hook(self)
        write_updated_config = write_updated_config(self)
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

    def _parse_config(self) -> TrackedAttrConfig:
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
        return TrackedAttrConfig(config,
                                 attr_update_hooks=self._attr_update_hooks,
                                 common_update_hook=write_updated_config)

    def _str_to_environ(self, environ_str: str) -> MonitoredEnviron[str, str]:
        keys_vals = map(lambda x: x.split('='), environ_str.strip().splitlines())
        env_dict = {k.strip(): v.strip() for k, v in keys_vals}
        return MonitoredEnviron(initial_env=dict(),
                                custom_vars=env_dict,
                                update_hook=self._environ_update_hook)

    def _str_to_list(self, modules_str: str) -> MonitoredList[str]:
        modules_list = [m.strip() for m in modules_str.strip().split(',')]
        return MonitoredList(modules_list, update_hook=self._modules_update_hook)

    def _str_to_type(
            self,
            key: str,
            value: str
    ) -> Union[str, bool, int, MonitoredEnviron[str, str], MonitoredList[str]]:
        if value == 'true':
            return True
        elif value == 'false':
            return False
        elif value.isdigit():
            return int(value)
        # two special cases
        elif key == 'environ':
            return self._str_to_environ(value)
        elif key == 'modules':
            return self._str_to_list(value)
        else:
            return value

    def write_config_file(self):
        # ADD DOCSTRING
        # called from inside the TrackedAttrConfig's update hook to write
        # changes to the original file and sync with remote, if connected
        with self.local_path.open('w') as f:
            self._configparser.write(f, space_around_delimiters=True)
        if self._cluster.connected:
            self.upload()
