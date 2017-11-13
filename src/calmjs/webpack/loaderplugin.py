# -*- coding: utf-8 -*-
"""
Loader plugin registry and handlers for webpack.

Currently a loader plugin registry for webpack is provided to allow the
mapping of named loader plugins to the intended locations.
"""

import shutil
from os import makedirs
from os.path import dirname
from os.path import exists
from os.path import join

from calmjs.loaderplugin import NPMLoaderPluginHandler


# TODO a generic npm-webpack plugin handler could be created, if the
# rules for the defaults are simple enough.

class WebpackLoaderHandler(NPMLoaderPluginHandler):

    def __call__(self, toolchain, spec, modname, source, target, modpath):
        # XXX this is only a partial implementation, no resolution of
        # nested/embedded loaders are done.
        stripped_modname = self.unwrap(modname)
        chained = (
            self.registry.get_record(stripped_modname)
            if '!' in stripped_modname else None)
        if chained:
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

        copy_target = join(spec['build_dir'], target)
        if not exists(dirname(copy_target)):
            makedirs(dirname(copy_target))
        shutil.copy(source, copy_target)

        modpaths = {modname: modpath}
        targets = {stripped_modname: target}
        export_module_names = [modname]
        return modpaths, targets, export_module_names


class TextPluginHandler(WebpackLoaderHandler):
    node_module_pkg_name = 'text-loader'
