from __future__ import annotations

import re
import time
from functools import wraps
from typing import Any, Callable, Dict, Literal, TYPE_CHECKING, TypeVar, Union

if TYPE_CHECKING:
    from clustertools.file_objects.configs.global_config import GlobalConfig
    from clustertools.file_objects.configs.project_config import ProjectConfig
    from clustertools.shared.environ import PseudoEnviron
    from clustertools.shared.object_monitors import MonitoredList
    from clustertools.shared.typing import (_BoundHook,
                                            _CheckedVal,
                                            _Config,
                                            _Hook,
                                            _UncheckedVal,
                                            EmailAddress,
                                            OneOrMore,
                                            WallTimeStr)


EMAIL_PATTERN = re.compile(r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$')


_T = TypeVar('_T')
class SimpleDefaultDict(dict):
    # ADD DOCSTRING
    """
    Similar to collections.defaultdict, but doesn't add missing keys.
    Accepts an additional keyword-only argument 'default' that may
    be either a default value to return for missing keys, or a
    callable that accepts the missing key as an argument.

    Used here to provide a dummy callable hook for config fields that
    don't require any special validation or extra work
    """
    def __init__(
            self,
            *arg,
            default: Union[_T, Callable[..., _T]] = None,
            **kwargs
    ) -> None:
        # ADD DOCSTRING
        if len(arg) > 1:
            raise TypeError(
                f"{self.__class__.__name__} expected at most 1 argument, got "
                f"{len(arg)}"
            )
        super().__init__(*arg, **kwargs)
        if callable(default):
            self.default = default
        else:
            self.default = lambda key: default

    def __missing__(self, key: Any) -> _T:
        return self.default(key)


def dummy_hook(inst: _Config, val: _T) -> _T:
    return val


########################################################################
#                         CONFIG HOOK HELPERS                          #
########################################################################
def bindable(
        func: _Hook[[_Config, _UncheckedVal], _CheckedVal]
) -> _BoundHook[[_UncheckedVal], _CheckedVal]:
    # ADD DOCSTRING - decorates a function 'func', allowing it to be
    #  bound to an object 'instance' at runtime and optionally added as
    #  an instance method
    @wraps(func)
    def bind(instance: _Config) -> _BoundHook:
        return func.__get__(instance)

    return bind


# def enforce_value_type(value: Any, _type: OneOrMore[Type]) -> None:
#     if not isinstance(value, _type):
#         if hasattr(_type, '__iter__'):
#             assert len(_type) == 2  # no fields should accept more than 2 types
#             t = f"either '{_type[0].__name__}' or '{_type[1].__name__}'"
#         else:
#             t = f"'{_type.__name__}'"
#         raise TypeError(
#             f"Type of assigned value must be {t}. Received "
#             f"'{value.__class__.__name__}'"
#         )


def environ_to_str(environ: Union[Dict[str, str], PseudoEnviron]) -> str:
    str_fmt = '\n'.join(' = '.join(item) for item in environ.items())
    if str_fmt != '':
        str_fmt = '\n' + str_fmt
    return str_fmt


@bindable
def write_updated_config(inst: _Config, keys_newvals: Dict[str, Any]) -> None:
    # TODO: just define this on BaseConfig instead?
    # called when any changes to the config object are made
    # keys_newvals is a dict of just-updated fields
    # function used for TrackedAttrConfig.common_update_hook
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


########################################################################
#                        MONITORED OBJECT HOOKS                        #
########################################################################
@bindable
def environ_post_update_global(inst: GlobalConfig) -> None:
    default_environ = inst._config.project_defaults.runtime_environment.environ
    environ_str = environ_to_str(default_environ)
    inst._configparser.set('project_defaults.runtime_environment',
                           'environ',
                           environ_str)
    inst.write_config_file()


@bindable
def environ_post_update_project(inst: ProjectConfig) -> None:
    environ_str = environ_to_str(inst._config.runtime_environment.environ)
    inst._configparser.set('runtime_environment', 'environ', environ_str)
    inst.write_config_file()


@bindable
def modules_post_update_global(inst: GlobalConfig) -> None:
    modules_str = ','.join(inst._config.project_defaults.runtime_environment.modules)
    inst._configparser.set('project_defaults.runtime_environment',
                           'modules',
                           modules_str)
    inst.write_config_file()


@bindable
def modules_post_update_project(inst: ProjectConfig) -> None:
    modules_str = ','.join(inst._config.runtime_environment.modules)
    inst._configparser.set('runtime_environment', 'modules', modules_str)
    inst.write_config_file()


def validate_email(email: OneOrMore[str]) -> None:
    # used by itself when individual items added to/replaced in
    # email_list and as part of 'validate_email_list' when entire field
    # is replaced

    is_valid = bool(email == 'INFER' or EMAIL_PATTERN.match(email))
    if not is_valid:
        raise ValueError(
            f"{email} does not appear to be formatted as a valid email "
            f"address (you can pass 'infer' to use the default email address "
            f"for your account)"
        )


@bindable
def email_post_update_global(inst: GlobalConfig) -> None:
    emails_str = ','.join(inst._config.project_defaults.notifications.email_list)
    inst._configparser.set('project_defaults.notifications',
                           'email_list',
                           emails_str)
    inst.write_config_file()


@bindable
def email_post_update_project(inst: ProjectConfig) -> None:
    emails_str = ','.join(inst._config.notifications.email_list)
    inst._configparser.set('notifications', 'email_list', emails_str)
    inst.write_config_file()


########################################################################
#                      SHARED HOOKS (BaseConfig)                       #
########################################################################
@bindable
def validate_job_basename(inst: _Config, new_basename: str) -> str:
    # TODO: should logic for preventing changes to attribute when
    #  submission/jobs in progress be handled here or on Project object?
    if len(new_basename) > 15:
        raise ValueError("Job names may be up to 15 characters in length")
    elif not new_basename[0].isalpha():
        raise ValueError(
            "Job names must start with an alphabetic character ([a-zA-Z])"
        )
    elif re.search('\s', new_basename) is not None:
        raise ValueError("Job names may not contain whitespace")
    return new_basename


@bindable
def validate_walltime_str(inst: _Config, walltime_str: str) -> WallTimeStr:
    try:
        time.strptime(walltime_str, '%H:%M:%S')
    except ValueError:
        try:
            time.strptime(walltime_str, '%M:%S')
        except ValueError:
            raise ValueError(
                "Malformed string value for 'wall_time'. Format should be "
                "'HH:MM:SS', or 'MM:SS' if requesting < 1 hour"
            )
    return walltime_str


BASE_CONFIG_UPDATE_HOOKS = {
    'job_basename': validate_job_basename,
    'wall_time': validate_walltime_str
}
BASE_CONFIG_UPDATE_HOOKS = SimpleDefaultDict(BASE_CONFIG_UPDATE_HOOKS)


########################################################################
#                         GLOBAL CONFIG HOOKS                          #
########################################################################
@bindable
def move_projects(inst: GlobalConfig, new_dir: str) -> str:
    # TODO: write me... this is a tricky one. will need to
    #  inst._cluster.check_output() a 'mv' command for each project in
    #  the old project_dir. Also should confirm
    #  inst._cluster.is_dir(PurePosixPath(new_dir)) first
    # enforce_value_type(value=new_dir, _type=str)
    raise NotImplementedError("Moving project directory is not yet supported")


# @bindable
# def launch_in_project_dir_hook(inst: GlobalConfig, pref: bool) -> None:
#     enforce_value_type(value=pref, _type=bool)


@bindable
def validate_shell_executable(inst: GlobalConfig, new_exe: str) -> str:
    # update cluster object, which conveniently validates executable
    # enforce_value_type(value=new_exe, _type=str)
    inst._cluster.executable = new_exe
    return new_exe


# @bindable
# def confirm_project_deletion_hook(inst: GlobalConfig, pref: bool) -> None:
#     enforce_value_type(value=pref, _type=bool)


@bindable
def check_default_prefer_value(
        inst: GlobalConfig,
        pref: Literal['local', 'remote', 'recent']
) -> None:
    if pref not in ('local', 'remote', 'recent'):
        raise ValueError(
            "default file syncing behavior must be either 'local', 'remote', "
            "or 'recent'"
        )


@bindable
def monitor_modules_global(
        inst: GlobalConfig,
        new_modules: OneOrMore[str]
) -> MonitoredList:
    # called when config field is *replaced*, rather than edited
    if isinstance(new_modules, str):
        new_modules = [new_modules]
    else:
        new_modules = list(new_modules)
    return MonitoredList(new_modules,
                         validate_item_hook=None,
                         post_update_hook=modules_post_update_global(inst))


@bindable
def monitor_email_list_global(
        inst: GlobalConfig,
        new_emails: OneOrMore[str]
) -> MonitoredList[EmailAddress]:
    if isinstance(new_emails, str):
        new_emails = [new_emails]
    else:
        new_emails = list(new_emails)
    for eml in new_emails:
        validate_email(eml)
    return MonitoredList(new_emails,
                         validate_item_hook=validate_email,
                         post_update_hook=email_post_update_global)


GLOBAL_CONFIG_UPDATE_HOOKS = {
    'project_dir': move_projects,
    'executable': validate_shell_executable,
    'default_prefer': check_default_prefer_value,
    'email_list': monitor_email_list_global
}
GLOBAL_CONFIG_UPDATE_HOOKS = SimpleDefaultDict(GLOBAL_CONFIG_UPDATE_HOOKS)


########################################################################
#                         PROJECT CONFIG HOOKS                         #
########################################################################
@bindable
def monitor_modules_project(
        inst: ProjectConfig,
        new_modules: OneOrMore[str]
) -> MonitoredList:
    # called when config field is *replaced*, rather than edited
    if isinstance(new_modules, str):
        new_modules = [new_modules]
    else:
        new_modules = list(new_modules)
    return MonitoredList(new_modules,
                         validate_item_hook=None,
                         post_update_hook=modules_post_update_project(inst))


@bindable
def update_config_from_global(inst: ProjectConfig, pref: bool) -> bool:
    # TODO: write me. This one's going to take some pre-planning &
    #  coordinating between ProjectConfig, Project, MonitoredEnviron,
    #  TrackedAttrConfig, etc. classes
    ...
    return pref


@bindable
def monitor_email_list_project(
        inst: ProjectConfig,
        new_emails: OneOrMore[str]
) -> MonitoredList[EmailAddress]:
    if isinstance(new_emails, str):
        new_emails = [new_emails]
    else:
        new_emails = list(new_emails)
    for eml in new_emails:
        validate_email(eml)
    return MonitoredList(new_emails,
                         validate_item_hook=validate_email,
                         post_update_hook=email_post_update_project)


PROJECT_CONFIG_UPDATE_HOOKS = {
    'modules': monitor_modules_project,
    'use_global_environ': update_config_from_global,
    'email_list': monitor_email_list_project
}
PROJECT_CONFIG_UPDATE_HOOKS = SimpleDefaultDict(PROJECT_CONFIG_UPDATE_HOOKS)
