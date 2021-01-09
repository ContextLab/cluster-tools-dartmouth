from __future__ import annotations

from configparser import ConfigParser
from typing import Any, Dict, Optional, TYPE_CHECKING

from clustertools.file_objects.configs.config_helpers import (
    BASE_CONFIG_UPDATE_HOOKS,
    BASE_OBJECT_VALIDATE_HOOKS,
    str_to_type,
    to_type_funcs,
    type_to_str
)
from clustertools.file_objects.synced_file import SyncedFile

if TYPE_CHECKING:
    from clustertools.cluster import Cluster
    from clustertools.file_objects.configs.tracked_attr_config import TrackedAttrConfig
    from clustertools.shared.typing import PathLike


class BaseConfig(SyncedFile):
    # ADD DOCSTRING
    def __init__(
            self,
            cluster: Cluster,
            local_path: PathLike,
            remote_path: Optional[PathLike] = None
    ) -> None:
        # ADD DOCSTRING
        # bind hooks to object *WITHOUT UPDATING THE ORIGINAL* - if the
        # original function object were modified, initializing a second
        # BaseConfig instance in the same session would fail
        # - needs to be done before call to super().__init__, which
        # triggers _init_local methods here and on subclasses.
        for field, hook in BASE_CONFIG_UPDATE_HOOKS.items():
            self._config_update_hooks[field] = hook(self)
        for field, hook in BASE_OBJECT_VALIDATE_HOOKS.items():
            self._object_validate_hooks[field] = hook(self)
        self._to_type_funcs = dict()
        for field, func in to_type_funcs.items():
            self._to_type_funcs[field] = func(self)
        self._str_to_type = str_to_type(self)
        super().__init__(cluster=cluster,
                         local_path=local_path,
                         remote_path=remote_path)

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
        # suppressing because inspection doesn't pick up return value
        # of decorated function
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
                # PyCharm doesn't recognize Callables returned by
                # decorated functions
                # noinspection PyCallingNonCallable
                section_dict[option] = self._str_to_type(option, value)
            if '.' in sec_name:
                sec_name, subsec_name = sec_name.split('.')
                config[sec_name][subsec_name] = section_dict
            else:
                config[sec_name] = section_dict
        return TrackedAttrConfig(config,
                                 attr_update_hooks=self._config_update_hooks,
                                 common_update_hook=self._write_updated_config)

    def _write_updated_config(self, keys_newvals: Dict[str, Any]) -> None:
        # called when any changes to the config object are made
        # keys_newvals is a dict of just-updated fields
        # function used for TrackedAttrConfig.common_update_hook
        any_changed = False
        for sec_name, section in self._configparser.items():
            if sec_name == 'DEFAULT':
                continue
            for option, value in section.items():
                if option in keys_newvals:
                    str_newval = type_to_str(value=keys_newvals[option])
                    if str_newval != value:
                        section[option] = str_newval
                        any_changed = True
                else:
                    continue
        if any_changed:
            self.write_config_file()

    def write_config_file(self):
        # ADD DOCSTRING
        # called from inside the TrackedAttrConfig's update hook to write
        # changes to the original file and sync with remote, if connected
        with self.local_path.open('w') as f:
            self._configparser.write(f, space_around_delimiters=True)
        if self._cluster.connected:
            self.upload()