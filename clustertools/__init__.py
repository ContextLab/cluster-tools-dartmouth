from pathlib import Path
from clustertools.cluster import Cluster

version_info = (0, 0, 1)
__version__ = '.'.join(map(str, version_info))

CLUSTERTOOLS_CONFIG_DIR = Path.home().joinpath('.clustertools')

# TODO: add logging functionality
# TODO: move all property setter docstrings to getters
# TODO: update type checking-related imports to conditionally import if
#  typing.TYPE_CHECKING is True to avoid circular imports
