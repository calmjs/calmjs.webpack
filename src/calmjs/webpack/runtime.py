# -*- coding: utf-8 -*-
"""
The calmjs runtime collection
"""

from argparse import SUPPRESS
from calmjs.argparse import metavar
from calmjs.runtime import SourcePackageToolchainRuntime

from calmjs.webpack.base import CALMJS_COMPAT
from calmjs.webpack.base import DEFAULT_BOOTSTRAP_EXPORT
from calmjs.webpack.base import WEBPACK_ENTRY_POINT
from calmjs.webpack.base import WEBPACK_OPTIMIZE_MINIMIZE
from calmjs.webpack.base import VERIFY_IMPORTS
from calmjs.webpack.dist import extras_calmjs_methods
from calmjs.webpack.dist import sourcepath_methods_map
from calmjs.webpack.dist import calmjs_module_registry_methods
from calmjs.webpack.cli import create_spec
from calmjs.webpack.cli import default_toolchain


class WebpackRuntime(SourcePackageToolchainRuntime):
    """
    Runtime for the WebpackToolchain

    Example: generate a webpack artifact

    $ calmjs webpack example.package
    """

    def __init__(
            self, toolchain, description='calmjs webpack bundler tool',
            *a, **kw):
        super(WebpackRuntime, self).__init__(
            cli_driver=toolchain, description=description, *a, **kw)

    def init_argparser_export_target(self, argparser):
        super(WebpackRuntime, self).init_argparser_export_target(
            argparser,
            help='output filename; defaults to last ${package_name}.js',
        )

    def init_argparser_working_dir(self, argparser):
        super(WebpackRuntime, self).init_argparser_working_dir(
            argparser,
            explanation=(
                'for this tool it will be used as the base directory for '
                'locating the node_modules for the declared bundled source '
                'files, and as the base directory for export_target and '
                'build_dir paths; '
            ),
        )

    def init_argparser_source_registry(self, argparser):
        super(WebpackRuntime, self).init_argparser_source_registry(
            argparser,
            help=(
                'comma separated list of registries to use for gathering '
                'JavaScript sources from the given Python packages; default '
                'behavior is to auto-select, enable verbose output to check '
                'to see which ones were selected'
            ),
        )

    def init_argparser(self, argparser):
        """
        Other runtimes (or users of ArgumentParser) can pass their
        subparser into here to collect the arguments here for a
        subcommand.
        """

        # applying the advanced options so they come before the global
        # options
        self.init_argparser_advanced_options(argparser)

        super(WebpackRuntime, self).init_argparser(argparser)

        argparser.add_argument(
            '--sourcepath-method', default='all',
            dest='sourcepath_method',
            choices=sorted(sourcepath_methods_map.keys()),
            help='the acquisition method for getting the source module to '
                 'filesystem path mappings from the source registry for the '
                 'given packages; default: all',
        )

        argparser.add_argument(
            '--source-registry-method', default='all',
            dest='source_registry_method',
            choices=sorted(calmjs_module_registry_methods.keys()),
            help='the acquisition method for getting the list of source '
                 'registries to use for the given packages; default: all',
        )

        argparser.add_argument(
            '--bundlepath-method', default='all',
            dest='bundlepath_method',
            choices=sorted(extras_calmjs_methods.keys()),
            help='the acquisition method for retrieving explicitly defined '
                 'bundled sources from Node.js module sources for the given '
                 'packages; default: all',
        )

        argparser.add_argument(
            '--optimize-minimize', action='store_true',
            dest=WEBPACK_OPTIMIZE_MINIMIZE,
            help='enable the optimize minimize option',
        )

        argparser.add_argument(
            '--skip-validate-imports', action='store_false',
            dest=VERIFY_IMPORTS, default=True,
            help="don't run the import validation; skip validation of imports "
                 "(i.e. define and require statements) across all input "
                 "source files for any unsatisfied declarations",
        )

        argparser.add_argument(
            '--validate-imports', action='store_true',
            dest=VERIFY_IMPORTS, help=SUPPRESS,
        )

    def init_argparser_advanced_options(self, argparser):
        """
        Advanced calmjs webpack specific options.
        """

        advanced_options = argparser.add_argument_group(
            'advanced optional arguments')

        advanced_options.add_argument(
            '--disable-calmjs-compat', action='store_false',
            dest=CALMJS_COMPAT, default=True,
            help="disable calmjs compatibility; i.e. don't include the "
                 "surrogate import loader module; disables support for "
                 "dynamic imports",
        )

        advanced_options.add_argument(
            '--webpack-entry-point', action='store',
            dest=WEBPACK_ENTRY_POINT, default=DEFAULT_BOOTSTRAP_EXPORT,
            metavar=metavar('module_alias'),
            help="explicitly specify the webpack entry point; only has effect "
                 "if --disable-calmjs-compat was specified and the provided "
                 "value must be aliased and available in the resulting "
                 "artifact; defaults to the calmjs generated module that "
                 "contains all discovered JavaScript modules",
        )

    def create_spec(
            self, source_package_names=(), export_target=None,
            working_dir=None,
            build_dir=None,
            calmjs_module_registry_names=None,
            source_registry_method='all',
            sourcepath_method='all', bundlepath_method='all',
            calmjs_compat=True,
            webpack_entry_point=DEFAULT_BOOTSTRAP_EXPORT,
            webpack_optimize_minimize=False,
            verify_imports=True,
            toolchain=None, **kwargs):
        """
        Accept all arguments, but also the explicit set of arguments
        that get passed down onto the toolchain.
        """

        # the spec takes a different set of keys as it will ultimately
        # derive the final values for the standardized spec keys.
        return create_spec(
            package_names=source_package_names,
            export_target=export_target,
            working_dir=working_dir,
            build_dir=build_dir,
            source_registry_method=source_registry_method,
            source_registries=calmjs_module_registry_names,
            sourcepath_method=sourcepath_method,
            bundlepath_method=bundlepath_method,
            calmjs_compat=calmjs_compat,
            webpack_entry_point=webpack_entry_point,
            webpack_optimize_minimize=webpack_optimize_minimize,
            verify_imports=verify_imports,
        )


default = WebpackRuntime(default_toolchain)
