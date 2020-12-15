from typing import Any, Dict

from clustertools.shared.helpers import bindable
# TODO: this is going to be circular...
from clustertools.file_objects.base_config import BaseConfig
from clustertools.file_objects.global_config import GlobalConfig
from clustertools.file_objects.project_config import ProjectConfig
from clustertools.shared.typing import EmailAddress, validate_email, validate_walltime, WallTimeStr


########################################################################
#                      SHARED HOOKS (BaseConfig)                       #
########################################################################
@bindable
def write_updated_config(inst: BaseConfig, keys_newvals: Dict[str, Any]) -> None:
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


@bindable
def email_update_hook(inst: BaseConfig, new_email: EmailAddress) -> None:
    validate_email(new_email)


@bindable
def wall_time_update_hook(inst: BaseConfig, new_walltime: WallTimeStr) -> None:
    validate_walltime(new_walltime)


BASE_CONFIG_UPDATE_HOOKS = {
    'email': email_update_hook,
    'wall_time': wall_time_update_hook
}


########################################################################
#                         GLOBAL CONFIG HOOKS                          #
########################################################################
@bindable
def project_dir_update_hook(inst: GlobalConfig, new_dir: str) -> None:
    # TODO: write me... this is a tricky one. will need to
    #  inst._cluster.check_output() a 'mv' command for each project in
    #  the old project_dir. Also should confirm
    #  inst._cluster.is_dir(PurePosixPath(new_dir)) first
    pass


@bindable
def executable_update_hook(inst: GlobalConfig, new_exe: str) -> None:
    # update cluster object, which conveniently validates executable
    inst._cluster.executable = new_exe




GLOBAL_CONFIG_UPDATE_HOOKS = {
    'project_dir': project_dir_update_hook,
    'executable': executable_update_hook
}


########################################################################
#                         PROJECT CONFIG HOOKS                         #
########################################################################
@bindable
def data_subdir_update_hook(inst: ProjectConfig, new_dir: str) -> None:
    # TODO: write me
    # require that it be a subdirectory (not is_absolute is probably the
    # closest possible check)
    # if self._project.doesnt_have_jobs_running:
        # inst._cluster.rename_the_data_dir
    pass


PROJECT_CONFIG_UPDATE_HOOKS = {
    'data_subdir': data_subdir_update_hook
}