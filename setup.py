# TODO:
#  write a post_install function that sets up ~/.clustertools
#  config directory with default global config and an empty projects/
#  dir. Test that it works for pip install from PyPI, tarball, local
#  git repo (regular and editable mode), and remote GitHub repo url

# TODO:
#  We should eventually switch to PEP 517-compliant install via
#  pyproject.toml, but I'm sticking with this for development since
#  setup.py is still required for editable installs during.
#  NOTE:
#  this will hopefully be resolved soon. Putting this here for later
#  reference:
#  https://github.com/pypa/pip/pull/6370#issuecomment-479938348

from setuptools import setup


setup()
