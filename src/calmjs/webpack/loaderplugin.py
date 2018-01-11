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
        copy_target = join(spec['build_dir'], target)
        if not exists(dirname(copy_target)):
            makedirs(dirname(copy_target))
        shutil.copy(source, copy_target)

        modpaths = {modname: modpath}
        targets = {stripped_modname: target}
        export_module_names = [modname]
        return modpaths, targets, export_module_names

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
        export_module_names = [
            self.name + '!' + v for v in inner_export_module_names]
        return modpaths, targets, export_module_names

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

    @property
    def node_module_pkg_name(self):
        return self.name + '-loader'


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
