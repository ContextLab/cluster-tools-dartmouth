from pathlib import Path
from clustertools.cluster import Cluster

version_info = (0, 0, 1)
__version__ = '.'.join(map(str, version_info))

CLUSTERTOOLS_CONFIG_DIR = Path.home().joinpath('.clustertools')
CLUSTERTOOLS_TEMPLATES_DIR = Path(__file__).resolve().parent.joinpath('templates')

# TODO: add logging functionality

# TODO: move all property setter docstrings to getters

# TODO: update type checking-related imports to conditionally import if
#  typing.TYPE_CHECKING is True to avoid circular imports

# TODO: write global 'configure' function so global config params can be
#  set via 'clustertools.configure'

# TODO: write global '_auto_detect_notebook' function that initializes
#  variables that control output appearance/behavior based on whether
#  clustertools was imported in a Jupyter Notebook
