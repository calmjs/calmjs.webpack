# -*- coding: utf-8 -*-
"""
Toolchain for using webpack with calmjs.
"""

from __future__ import unicode_literals

import codecs
import json
import logging
import sys
from os.path import basename
from os.path import dirname
from os.path import join
from os.path import exists
from os.path import isdir
from os.path import pathsep
from subprocess import call

from calmjs.toolchain import Toolchain
from calmjs.toolchain import CONFIG_JS_FILES
from calmjs.toolchain import EXPORT_TARGET
from calmjs.toolchain import EXPORT_MODULE_NAMES
from calmjs.toolchain import BUILD_DIR

from .env import webpack_env
from .env import NODE_MODULES
from .exc import WebpackRuntimeError
from .exc import WebpackExitError


logger = logging.getLogger(__name__)

# The spec key for storing the base webpack configuration.
WEBPACK_CONFIG = 'webpack_config'
# The key for the default module name, use as the webpack library name
WEBPACK_DEFAULT_MODULE_NAME = 'webpack_default_module_name'

# other private values

_PLATFORM_SPECIFIC_RUNTIME = {
    'win32': 'webpack.cmd',
}
_DEFAULT_RUNTIME = 'webpack'
_DEFAULT_MODULE_NAME = '__calmjs__'


# TODO figure out how to deal with chunking configuration
_WEBPACK_CONFIG_TEMPLATE = """'use strict';

var webpack = require('webpack');

var webpackConfig = (
%s
)

module.exports = webpackConfig;
module.exports.plugins = [
    new webpack.optimize.LimitChunkCountPlugin({maxChunks: 1})
];
"""

# TODO also figure out whether or not/how to best allow the __calmjs__
# be additionally applied.
# XXX most direct way is to manipulate window.__calmjs__, however this
# should be checked to be the right way.  Also this assumes the defaults
# have been used.
_WEBPACK_CALMJS_MODULE_TEMPLATE = """'use strict';
exports.modules = {
%s
};

exports.require = function(modules, f) {
    if (modules.map) {
        f.apply(null, modules.map(function(m) {
            return exports.modules[m];
        }));
    }
    else {
        // assuming the synchronous version
        return exports.modules[modules];
    }
};
"""


def get_webpack_runtime_name(platform):
    return _PLATFORM_SPECIFIC_RUNTIME.get(platform, _DEFAULT_RUNTIME)


def _null_transpiler(spec, reader, writer):
    line = reader.readline()
    while line:
        writer.write(line)
        line = reader.readline()


def _webpack_transpiler(spec, reader, writer):
    # ensure the reader is done from beginning
    # TODO transpiler to convert dynamic require to using the __calmjs__
    # loader.
    # It will need to rewrite
    # require(<non_string>
    # into
    # require('__calmjs__').require(<non_string>
    reader.seek(0)
    return _null_transpiler(spec, reader, writer)


class WebpackToolchain(Toolchain):
    """
    The toolchain that make use of webpack to generate an artifact.
    """

    webpack_bin_key = 'webpack_bin'
    webpack_bin = get_webpack_runtime_name(sys.platform)
    webpack_config_name = 'config.js'

    def __init__(self, *a, **kw):
        super(WebpackToolchain, self).__init__(*a, **kw)
        self.binary = self.webpack_bin
        self._set_env_path_with_node_modules()

    def setup_transpiler(self):
        self.transpiler = _webpack_transpiler

    def prepare(self, spec):
        """
        Attempts to locate the webpack binary if not already specified;
        raise WebpackRuntimeError if that is not found.
        """

        if self.webpack_bin_key not in spec:
            which_bin = spec[self.webpack_bin_key] = (
                self.which() or self.which_with_node_modules())
            if which_bin is None:
                raise WebpackRuntimeError(
                    "unable to locate '%s'" % self.binary)
            logger.debug("using '%s' as '%s'", which_bin, self.binary)
        elif not exists(spec[self.webpack_bin_key]):
            # should we check whether target can be executed?
            raise WebpackRuntimeError(
                "'%s' does not exist; cannot be used as '%s' binary" % (
                    spec[self.webpack_bin_key],
                    self.webpack_bin
                )
            )

        spec['webpack_config_js'] = join(
            spec[BUILD_DIR], self.webpack_config_name)

        if EXPORT_TARGET not in spec:
            raise WebpackRuntimeError(
                "'%s' not found in spec" % EXPORT_TARGET)

        # no effect if EXPORT_TARGET already absolute.
        spec[EXPORT_TARGET] = self.join_cwd(spec[EXPORT_TARGET])
        spec[CONFIG_JS_FILES] = [spec['webpack_config_js']]

        if WEBPACK_DEFAULT_MODULE_NAME not in spec:
            spec[WEBPACK_DEFAULT_MODULE_NAME] = _DEFAULT_MODULE_NAME

        logger.debug(
            'webpack.output.library = %s', json.dumps(
                spec[WEBPACK_DEFAULT_MODULE_NAME]))

        if not isdir(dirname(spec[EXPORT_TARGET])):
            raise WebpackRuntimeError(
                "'%s' will not be writable" % EXPORT_TARGET)
        logger.debug(
            "%s declared to be '%s'",
            EXPORT_TARGET, spec[EXPORT_TARGET]
        )

        keys = ('webpack_config_js',)
        matched = [k for k in keys if spec[EXPORT_TARGET] == spec[k]]

        if matched:
            raise WebpackRuntimeError(
                "'%s' must not be same as '%s'" % (EXPORT_TARGET, matched[0]))

        # TODO setup dev advice when implemented.
        # webpack_dev_advice(spec)

    def generate_lookup_module(self, spec):
        """
        Webpack does not provide an extensible named module system, so
        we have to build our own here...
        """

        exported = [
            "    %(module)s: require(%(module)s)," % {'module': json.dumps(m)}
            for m in spec[EXPORT_MODULE_NAMES]
            if '!' not in m  # lazily filter out loader modules
        ]

        export_module_path = join(
            spec[BUILD_DIR], spec[WEBPACK_DEFAULT_MODULE_NAME] + '.js')
        with codecs.open(export_module_path, 'w', encoding='utf8') as fd:
            fd.write(_WEBPACK_CALMJS_MODULE_TEMPLATE % '\n'.join(exported))
        return export_module_path

    def assemble(self, spec):
        """
        Assemble the library by compiling everything and generate the
        required files for the final bundling.
        """

        # the build config is the file that will be passed to webpack for
        # building the final bundle.
        webpack_config = {
            'output': {
                'path': dirname(spec[EXPORT_TARGET]),
                'filename': basename(spec[EXPORT_TARGET]),
                'libraryTarget': 'umd',  # XXX magic,
                'library': spec[WEBPACK_DEFAULT_MODULE_NAME],
                # TODO determine publicPath
            },
            'resolve': {},
        }

        webpack_config['entry'] = self.generate_lookup_module(spec)
        webpack_config['resolve']['alias'] = alias = {
            spec[WEBPACK_DEFAULT_MODULE_NAME]: webpack_config['entry'],
        }
        # generate the aliases - yes, we include the bundled sources to
        # be explicit as there are cases where an alternative bundle may
        # be specified using optional advices.
        source_prefixes = ('transpiled', 'bundled')
        for prefix in source_prefixes:
            key = prefix + '_targets'
            for modname, target in spec[key].items():
                # XXX lazily filter out any potential loader modules
                # XXX should only copy the ultimate final fragment into
                # the target dir.
                if '!' in modname:
                    continue
                # the alias must point to the full path.
                alias[modname] = join(spec[BUILD_DIR], *target.split('/'))

        # write out the configuration file
        with codecs.open(
                spec['webpack_config_js'], 'w', encoding='utf8') as fd:
            fd.write(_WEBPACK_CONFIG_TEMPLATE % json.dumps(
                webpack_config, indent=4))

        # record the webpack config to the spec
        spec[WEBPACK_CONFIG] = webpack_config

    def _find_node_modules(self):
        # TODO merge with upstream, or have upstream provide one by
        # splitting up which_with_node_modules
        paths = (self.node_path or str('')).split(pathsep)
        paths.append(self.join_cwd(NODE_MODULES))
        paths = [p for p in paths if isdir(p)]
        if not paths:
            logger.warning(
                'no valid node_modules found - webpack may fail to locate '
                'itself.'
            )
        return pathsep.join(paths)

    def link(self, spec):
        """
        Basically link everything up as a bundle, as if statically
        linking everything into "binary" file.
        """

        node_path = self._find_node_modules()
        # TODO allow to (un)set option flags such as --display-reasons
        args = (
            spec[self.webpack_bin_key],
            '--display-modules', '--display-reasons',
            '--config', spec['webpack_config_js']
        )
        logger.info('invoking WEBPACK=%r %s %s %s %s %s', node_path, *args)
        # note that webpack treats the configuration as an executable
        # node.js program - so that it will need to be able to import
        # (require) webpack - explicitly have to provide the one located
        # or associated with this toolchain instance, i.e. the one at
        # the current directory

        rc = call(args, env=webpack_env(node_path))
        if rc != 0:
            logger.error("webpack has encountered a fatal error")
            raise WebpackExitError(rc, spec[self.webpack_bin_key])
