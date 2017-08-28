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
# The key for generating a combined single test index.
WEBPACK_SINGLE_TEST_BUNDLE = 'webpack_single_test_bundle'
# The key for webpack externals
WEBPACK_EXTERNALS = 'webpack_externals'
# The key for specifying the raw entry point - the alias will need to be
# resolved to the actual webpack_entry.
WEBPACK_ENTRY_POINT = 'webpack_entry_point'
# Enable the --optimize-minimize option for webpack
WEBPACK_OPTIMIZE_MINIMIZE = 'webpack_optimize_minimize'

# constants

# The calmjs loader name
DEFAULT_CALMJS_EXPORT_NAME = '__calmjs_loader__'

# The webpack.library.export default name
DEFAULT_BOOTSTRAP_EXPORT = '__calmjs__'

# The bootstrap for commonjs global module usage - this has a number of
# caveats and really not recommended for usage.  To use the resulting
# artifact directly within node, the 'global' package from npm must be
# installed, and the result of the import must be assigned to __calmjs__
# in order for the chaining to work.  Example:
#
# > var __calmjs__ = require('./framework.js');
# ...
# > __calmjs__ = require('./widget.js');
# { require: [Function],
#   modules:
#    { 'widget/core': { Core: 'framework.lib.Core/widget.core.Core' },
# ... } }
#
# Naturally, this is NOT supported, but done so to make it possible to
# use.
DEFAULT_BOOTSTRAP_COMMONJS = ('global', DEFAULT_BOOTSTRAP_EXPORT)

# the compelted default config.
DEFAULT_BOOTSTRAP_EXPORT_CONFIG = {
    "commonjs": list(DEFAULT_BOOTSTRAP_COMMONJS),
    "commonjs2": list(DEFAULT_BOOTSTRAP_COMMONJS),
    "root": DEFAULT_BOOTSTRAP_EXPORT,
    "amd": DEFAULT_BOOTSTRAP_EXPORT,
}
