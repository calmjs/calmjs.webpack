# -*- coding: utf-8 -*-
"""
Base classes and constants.
"""

from __future__ import unicode_literals

# keys

# The spec key for storing the base webpack configuration.
WEBPACK_CONFIG = 'webpack_config'
# The key for the webpack.output.library
WEBPACK_OUTPUT_LIBRARY = 'webpack_output_library'
# The key for webpack externals
WEBPACK_EXTERNALS = 'webpack_externals'
# The key for specifying the raw entry point - the alias will need to be
# resolved to the actual webpack_entry.
WEBPACK_ENTRY_POINT = 'webpack_entry_point'

# constants

# The calmjs loader name
DEFAULT_CALMJS_EXPORT_NAME = '__calmjs_loader__'
# The webpack.library.export default name
DEFAULT_BOOTSTRAP_EXPORT = '__calmjs__'
DEFAULT_BOOTSTRAP_EXPORT_CONFIG = {
    "root": DEFAULT_BOOTSTRAP_EXPORT,
    "amd": DEFAULT_BOOTSTRAP_EXPORT,
}
