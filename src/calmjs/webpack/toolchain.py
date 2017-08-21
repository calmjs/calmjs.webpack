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

# this may be deprecated/removed in the future, so we are doing this for
# type checking only to make use of calmjs.parse
from calmjs.vlqsm import SourceWriter

from calmjs.toolchain import Toolchain
from calmjs.toolchain import CONFIG_JS_FILES
from calmjs.toolchain import EXPORT_TARGET
from calmjs.toolchain import EXPORT_MODULE_NAMES
from calmjs.toolchain import BUILD_DIR

from calmjs.parse.exceptions import ECMASyntaxError
from calmjs.parse.parsers.es5 import parse
from calmjs.parse.unparsers.es5 import pretty_printer
from calmjs.parse import sourcemap

from calmjs.webpack.manipulation import convert_dynamic_require

from .env import webpack_env
from .env import NODE_MODULES
from .exc import WebpackRuntimeError
from .exc import WebpackExitError

from .base import WEBPACK_CONFIG
from .base import WEBPACK_EXTERNALS
from .base import WEBPACK_OUTPUT_LIBRARY
from .base import WEBPACK_ENTRY_POINT
from .base import DEFAULT_BOOTSTRAP_EXPORT
from .base import DEFAULT_BOOTSTRAP_EXPORT_CONFIG

logger = logging.getLogger(__name__)

# other private values

_PLATFORM_SPECIFIC_RUNTIME = {
    'win32': 'webpack.cmd',
}
_DEFAULT_RUNTIME = 'webpack'
_DEFAULT_BOOTSTRAP_FILENAME = '__calmjs_bootstrap__.js'


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

# TODO document how this will ONLY work for libraryTarget: "window", but
# the target will still be specified as umd to simplify interrogation
# of the generated bundles.
_WEBPACK_CALMJS_BOOTSTRAP_MODULE_TEMPLATE = """'use strict';

var calmjs_bootstrap = require('__calmjs__') || {};
exports.modules = calmjs_bootstrap.modules || {};
%s

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

# only exports _all_ modules
_WEBPACK_CALMJS_EXPORT_MODULE_TEMPLATE = """'use strict';

exports.modules = {};
%s
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
    reader.seek(0)
    # since calmjs.parse offers a comprehensive solution, the need for
    # a custom half-baked class should be stripped.
    stream = writer.stream if isinstance(writer, SourceWriter) else writer
    # do the conversion
    try:
        tree = parse(reader.read())
    except ECMASyntaxError:
        # XXX plugin handlers should prevent it from getting to this
        # stage.
        return _null_transpiler(spec, reader, writer)
    names, mappings = sourcemap.write(pretty_printer()(
        convert_dynamic_require(tree)), stream)
    # tack that back on
    if isinstance(writer, SourceWriter):
        writer.mappings = mappings
    # else, solution TBD


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

        spec[WEBPACK_EXTERNALS] = spec.get(WEBPACK_EXTERNALS, {})

    def generate_lookup_module(self, spec, template):
        """
        Webpack does not provide an extensible named module system, so
        we have to build our own here...
        """

        exported = [
            "exports.modules[%(module)s] = require(%(module)s);" % {
                'module': json.dumps(m)
            }
            for m in spec[EXPORT_MODULE_NAMES]
            if '!' not in m  # lazily filter out loader modules
        ]

        export_module_path = join(
            spec[BUILD_DIR], _DEFAULT_BOOTSTRAP_FILENAME)
        with codecs.open(export_module_path, 'w', encoding='utf8') as fd:
            fd.write(template % '\n'.join(exported))
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
                # TODO determine if publicPath is needed.

                # XXX Currently using magic values.  The library target
                # should be configured, along with umdNamedDefine also
                # when the way to expose the relevant options as proper
                # sets are determined.
                'libraryTarget': 'umd',
                'umdNamedDefine': True,
            },
            'resolve': {},
            'externals': spec.get(WEBPACK_EXTERNALS, {}),
        }
        if WEBPACK_OUTPUT_LIBRARY in spec:
            webpack_config['output']['library'] = spec[WEBPACK_OUTPUT_LIBRARY]

        # set up alias lookup mapping.
        webpack_config['resolve']['alias'] = alias = {}

        # generate the aliases - yes, we include the bundled sources to
        # be explicit as there are cases where an alternative bundle may
        # be specified using optional advices.
        source_prefixes = ('transpiled', 'bundled')
        for prefix in source_prefixes:
            key = prefix + '_targetpaths'
            for modname, target in spec[key].items():
                # XXX lazily filter out any potential loader modules
                # XXX should only copy the ultimate final fragment into
                # the target dir.
                if '!' in modname:
                    continue
                # the alias must point to the full path.
                alias[modname] = join(spec[BUILD_DIR], *target.split('/'))

        # It is assumed that if WEBPACK_ENTRY_POINT is defined, it will
        # resolve into a target through the generated alias mapping.
        # Otherwise, assume one of the default calmjs style exports.
        if (spec.get(WEBPACK_ENTRY_POINT, DEFAULT_BOOTSTRAP_EXPORT) ==
                DEFAULT_BOOTSTRAP_EXPORT):
            # now resolve whether the webpack.externals has been defined
            # in a manner that requires the complete lookup module
            logger.info(
                "spec webpack_entry_point defined to be '%s'",
                DEFAULT_BOOTSTRAP_EXPORT
            )
            if (spec[WEBPACK_EXTERNALS].get(DEFAULT_BOOTSTRAP_EXPORT) ==
                    DEFAULT_BOOTSTRAP_EXPORT_CONFIG):
                logger.info(
                    "webpack.externals defined '%s' with value that enables "
                    "the calmjs webpack bootstrap module; generating module "
                    "with the complete bootstrap template",
                    DEFAULT_BOOTSTRAP_EXPORT
                )
                webpack_config['entry'] = self.generate_lookup_module(
                    spec, _WEBPACK_CALMJS_BOOTSTRAP_MODULE_TEMPLATE)
                if (spec.get(WEBPACK_OUTPUT_LIBRARY) !=
                        DEFAULT_BOOTSTRAP_EXPORT):
                    # a simple warning will do, as this may only be an
                    # inconvenience.
                    logger.warning(
                        "exporting complete calmjs bootstrap module with "
                        "webpack.output.library as '%s' (expected '%s')",
                        spec.get(WEBPACK_OUTPUT_LIBRARY),
                        DEFAULT_BOOTSTRAP_EXPORT,
                    )
            else:
                logger.info(
                    "webpack.externals does not have '%s' defined for "
                    "the complete calmjs webpack bootstrap module",
                    DEFAULT_BOOTSTRAP_EXPORT
                )
                webpack_config['entry'] = self.generate_lookup_module(
                    spec, _WEBPACK_CALMJS_EXPORT_MODULE_TEMPLATE)
                if (spec.get(WEBPACK_OUTPUT_LIBRARY) ==
                        DEFAULT_BOOTSTRAP_EXPORT):
                    logger.critical(
                        "cowardly aborting export to webpack.output.library "
                        "as '%s' without the complete bootstrap; generating "
                        "module with export only template",
                        DEFAULT_BOOTSTRAP_EXPORT,
                    )
                    raise ValueError(
                        "aborting export of webpack.output.library as '%s' "
                        "with incomplete settings and bootstrap module" %
                        DEFAULT_BOOTSTRAP_EXPORT
                    )
        else:
            # need to manually resolve the entry
            # if externals has been defined, use the complete lookup module
            # otherwise, use the simplified version.
            webpack_config['entry'] = alias[spec[WEBPACK_ENTRY_POINT]]

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
