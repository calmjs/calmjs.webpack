# -*- coding: utf-8 -*-
"""
Loader plugin registry and handlers for webpack.

Currently a loader plugin registry for webpack is provided to allow the
mapping of named loader plugins to the intended locations.
"""

import shutil
import logging
from os import makedirs
from os.path import dirname
from os.path import exists
from os.path import join

from calmjs.loaderplugin import ModuleLoaderRegistry
from calmjs.npm import locate_package_entry_file
from calmjs.toolchain import BUILD_DIR
from calmjs.toolchain import WORKING_DIR
from calmjs.webpack.base import WEBPACK_MODULE_RULES
from calmjs.webpack.base import CALMJS_WEBPACK_MODULE_LOADER_SUFFIX
from calmjs.webpack.base import CALMJS_WEBPACK_MODNAME_LOADER_MAP
from calmjs.webpack.base import WebpackModuleLoaderRegistryKey

from calmjs.loaderplugin import LoaderPluginRegistry
from calmjs.loaderplugin import LoaderPluginHandler
from calmjs.loaderplugin import NPMLoaderPluginHandler

logger = logging.getLogger(__name__)


class BaseWebpackLoaderHandler(LoaderPluginHandler):
    """
    The base webpack loader implementation that works well for data file
    argument that are supplied by the final loader, that will also
    require copying.

    Subclasses may override the run method for specific purposes.  One
    possible way is to supply the original source file as the target,
    if it is infeasible to be copied (due to size and/or the processing
    is meant to be done through the specific webpack loader).
    """

    def run(self, toolchain, spec, modname, source, target, modpath):
        stripped_modname = self.unwrap(modname)
        copy_target = join(spec[BUILD_DIR], target)
        if not exists(dirname(copy_target)):
            makedirs(dirname(copy_target))
        # TODO make use of spec/toolchain copy manifest/function,
        # if/when that is implemented for source/dest tracking?
        # this may be useful to reduce the amount of data moved around.
        shutil.copy(source, copy_target)

        modpaths = {modname: modpath}
        targets = {
            stripped_modname: target,
            # Also include the relative path as a default alias so that
            # within the context of the loader, any implicit joining of
            # the current directory (i.e. './') with any declared
            # modnames within the system will not affect the ability to
            # do bare imports (e.g. "namespace/package/resource.data")
            # within the loader's interal import system.
            #
            # Seriously, forcing the '~' prefixes on all user imports
            # is simply unsustainable importability.
            './' + stripped_modname: target,
        }

        # while it is possible (and tempting) to return the modname
        # directly for the final mapping, the chaining through different
        # loaders can complicate this (also it makes little sense under
        # webpack to do so for a loader prefix-free not module), so just
        # simply don't.
        if spec.get(CALMJS_WEBPACK_MODNAME_LOADER_MAP, {}).get(
                stripped_modname):
            return modpaths, targets, []

        return modpaths, targets, self.finalize_export_module_names(
            toolchain, spec, [modname])

    def chained_call(
            self, chained,
            toolchain, spec, stripped_modname, source, target, modpath):
        # In general, only the innermost item matters.
        inner_modpaths, targets, inner_export_module_names = (
            chained.__call__(
                toolchain, spec, stripped_modname, source, target, modpath)
        )
        # need to wrap the inner_modpaths with the plugin name for
        # the values that export as modname
        modpaths = {
            self.name + '!' + k: v
            for k, v in inner_modpaths.items()
        }
        return modpaths, targets, self.finalize_export_module_names(
                toolchain, spec, inner_export_module_names, self.name)

    def generate_export_module_names(
            self, toolchain, spec, export_module_names, prefix=''):
        if prefix:
            return [prefix + '!' + v for v in export_module_names]
        return list(export_module_names)

    def finalize_export_module_names(
            self, toolchain, spec, export_module_names, prefix=''):
        """
        The standard method for finalizing the export module names
        produced for modules that involve the module loader syntax.
        These are the names that will end up in the generated calmjs
        export module.
        """

        return self.generate_export_module_names(
            toolchain, spec, export_module_names, prefix)

    def __call__(self, toolchain, spec, modname, source, target, modpath):
        stripped_modname = self.unwrap(modname)
        chained = (
            self.registry.get_record(stripped_modname)
            if '!' in stripped_modname else None)
        if chained:
            return self.chained_call(
                chained,
                toolchain, spec, stripped_modname, source, target, modpath,
            )

        return self.run(toolchain, spec, modname, source, target, modpath)


class WebpackLoaderHandler(NPMLoaderPluginHandler, BaseWebpackLoaderHandler):
    """
    The default webpack loader handler class.

    Typically, webpack loaders are sourced from npm under packages that
    are called {name}-loader, where the name is the name of the loader.
    This greatly simplifies how the loaders can be constructed and
    resolved.
    """

    # subclasses that expect an explicit npm package name, define this
    # node_module_pkg_name = ''

    def find_node_module_pkg_name(self, toolchain, spec):
        # since most loaders end with this suffix, test for that first
        if self.name.endswith('-loader'):
            return self.name

        # given that there will be packages that could have been
        # installed that matches the package name, test for the common
        # prefix first
        name = self.name + '-loader'
        # using the same working_dir derivation method as parent
        working_dir = spec.get(WORKING_DIR, toolchain.join_cwd())
        if locate_package_entry_file(working_dir, name):
            return name
        elif locate_package_entry_file(working_dir, self.name):
            return self.name

        # a value must be provided, but to not confuse with the
        # resolution of the real package, return the suffixed version
        return name


class AutogenWebpackLoaderHandler(WebpackLoaderHandler):
    """
    Special class for the default loader registry.
    """


class AutogenWebpackLoaderPluginRegistry(LoaderPluginRegistry):
    """
    A special registry that will construct/return a loader handler class
    for cases where they are not available.
    """

    def get_record(self, name):
        rec = super(AutogenWebpackLoaderPluginRegistry, self).get_record(name)
        if rec:
            return rec

        plugin_name = self.to_plugin_name(name)
        logger.debug(
            "%s registry '%s' generated loader handler '%s'",
            self.__class__.__name__, self.registry_name, plugin_name
        )
        return AutogenWebpackLoaderHandler(self, plugin_name)


class WebpackModuleLoaderRegistry(ModuleLoaderRegistry):
    """
    This webpack specific version will not include the loader prefixes
    in the generated names, however it will provide a reverse mapping
    which should be called to set up the loader chain.
    """

    def resolve_parent_registry_name(
            self, registry_name, suffix=CALMJS_WEBPACK_MODULE_LOADER_SUFFIX):
        return super(
            WebpackModuleLoaderRegistry, self
        ).resolve_parent_registry_name(registry_name, suffix)

    def generate_complete_modname(self, prefix, modname, extension):
        return WebpackModuleLoaderRegistryKey(prefix, modname + extension)


def normalize_and_register_webpackloaders(spec, sourcepath_map):
    """
    Given that we want to rely on the existing loaderplugin processing
    framework provided by the toolchain system, but we also want to
    accept sourcepath maps with keys provided by the previous registry,
    those keys must be converted to form accepted by the toolchain.
    Fortunately, we can rely on the standard loader syntax, as the keys
    provided can be treated as markers to note that they should be
    processed as webpack module.loaders to enable prefix-free imports
    from within webpack.

    Takes a spec and an unprocessed sourcepath mapping, and returns a
    new mapping with the special keys converted to the standard loader
    prefixed syntax, after marking them in the spec.
    """

    result = {}
    spec[WEBPACK_MODULE_RULES] = []
    mapping = spec[CALMJS_WEBPACK_MODNAME_LOADER_MAP] = spec.get(
        CALMJS_WEBPACK_MODNAME_LOADER_MAP, {})
    for key, path in sourcepath_map.items():
        if isinstance(key, WebpackModuleLoaderRegistryKey):
            result['%s!%s' % key] = path
            mapping[key.modname] = key.loader.split('!')
        else:
            result[key] = path
    return result


def update_spec_webpack_loaders_modules(spec, alias):
    """
    This transforms the module names that may be set up by the previous
    function to the actual real path that is required for the webpack
    configuration to effect the loaders stored inside module.rules.
    Specifically, the full path to the original file must be provided.
    """

    spec[WEBPACK_MODULE_RULES] = spec.get(WEBPACK_MODULE_RULES, [])
    modname_loader_map = spec.get(CALMJS_WEBPACK_MODNAME_LOADER_MAP, {})
    for modname, loaders in modname_loader_map.items():
        targetpath = alias.get(modname)
        if not targetpath:
            logger.warning(
                "WARNING modname '%s' requires loader chain %r but it does "
                "not have a corresponding webpack resolve.alias; "
                "webpack build failure may result as loaders are "
                "not configured for this modname", modname, loaders,
            )
            continue
        spec[WEBPACK_MODULE_RULES].append({
            'test': targetpath,
            'loaders': loaders,
        })
