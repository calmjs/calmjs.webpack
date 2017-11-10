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

class TextPluginHandler(NPMLoaderPluginHandler):

    node_module_pkg_name = 'text-loader'

    def __call__(self, toolchain, spec, modname, source, target, modpath):
        # XXX this is only a partial implementation, no resolution of
        # nested/embedded loaders are done.
        stripped_modname = self.unwrap(modname)
        copy_target = join(spec['build_dir'], target)
        if not exists(dirname(copy_target)):
            makedirs(dirname(copy_target))
        shutil.copy(source, copy_target)

        bundled_modpaths = {modname: modpath}
        bundled_targets = {stripped_modname: target}
        export_module_names = [modname]
        return bundled_modpaths, bundled_targets, export_module_names
