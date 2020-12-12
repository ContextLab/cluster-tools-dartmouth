from typing import Any, Dict

from clustertools.shared.helpers import bindable
# TODO: this is going to be circular...
from clustertools.file_objects.base_config import BaseConfig


@bindable
def write_updated_values(inst: BaseConfig, keys_newvals: Dict[str, Any]) -> None:
    any_changed = False
    for sec_name, section in inst._configparser.items():
        if sec_name == 'DEFAULT':
            continue
        for option, value in section.items():
            if option in keys_newvals:
                str_newval = inst._type_to_str(key=option, value=keys_newvals[option])
                if str_newval != value:
                    section[option] = str_newval
                    any_changed = True
            else:
                continue
    if any_changed:
        inst.write_config_file()