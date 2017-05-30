# -*- coding: utf-8 -*-
"""
The calmjs runtime collection
"""

from calmjs.runtime import SourcePackageToolchainRuntime

from calmjs.webpack.dist import extras_calmjs_methods
from calmjs.webpack.dist import source_map_methods_list
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
            self, toolchain, description='webpack bundler tool', *a, **kw):
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
                'for this tool it will be used as the base directory to '
                'find source files declared for bundling; '
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

        super(WebpackRuntime, self).init_argparser(argparser)

        argparser.add_argument(
            '--source-map-method', default='all',
            dest='source_map_method',
            choices=sorted(source_map_methods_list.keys()),
            help='the acquisition method for getting the source mappings from '
                 'the source registry for the given packages; default: all',
        )

        argparser.add_argument(
            '--source-registry-method', default='all',
            dest='source_registry_method',
            choices=sorted(calmjs_module_registry_methods.keys()),
            help='the acquisition method for getting the list of source '
                 'registries to use for the given packages; default: all',
        )

        argparser.add_argument(
            '--bundle-map-method', default='all',
            dest='bundle_map_method',
            choices=sorted(extras_calmjs_methods.keys()),
            help='the acquisition method for the bundle sources for the given '
                 'packages; default: all',
        )

    def create_spec(
            self, source_package_names=(), export_target=None,
            working_dir=None,
            build_dir=None,
            calmjs_module_registry_names=None,
            source_registry_method='all',
            source_map_method='all', bundle_map_method='all',
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
            source_map_method=source_map_method,
            bundle_map_method=bundle_map_method,
        )


default = WebpackRuntime(default_toolchain)
