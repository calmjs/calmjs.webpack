# -*- coding: utf-8 -*-
"""
Base classes and constants.
"""

from __future__ import unicode_literals

# keys

# The spec key for storing the base webpack configuration.
WEBPACK_CONFIG = 'webpack_config'
# The key for the default module name, use as the webpack library name
WEBPACK_DEFAULT_MODULE_NAME = 'webpack_default_module_name'
# The key for the webpack.output.library
WEBPACK_OUTPUT_LIBRARY = 'webpack_output_library'
# The key for webpack externals
WEBPACK_EXTERNALS = 'webpack_externals'

# constants
DEFAULT_BOOTSTRAP_EXPORT = '__calmjs__'
