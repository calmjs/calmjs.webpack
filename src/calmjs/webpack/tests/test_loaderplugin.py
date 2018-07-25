# -*- coding: utf-8 -*-
import unittest
import os
from os.path import exists
from os.path import join
from pkg_resources import working_set as root_working_set
from pkg_resources import Requirement

from calmjs.module import ModuleRegistry
from calmjs.loaderplugin import LoaderPluginRegistry
from calmjs.webpack import loaderplugin
from calmjs.webpack.base import WebpackModuleLoaderRegistryKey
from calmjs.webpack.loaderplugin import AutogenWebpackLoaderPluginRegistry
from calmjs.webpack.loaderplugin import WebpackModuleLoaderRegistry
from calmjs.webpack.loaderplugin import normalize_and_register_webpackloaders
from calmjs.webpack.loaderplugin import update_spec_webpack_loaders_modules

from calmjs.toolchain import Spec
from calmjs.toolchain import Toolchain
from calmjs.utils import pretty_logging
from calmjs.testing.utils import mkdtemp
from calmjs.testing.utils import remember_cwd
from calmjs.testing.mocks import StringIO
from calmjs.testing.mocks import WorkingSet
from calmjs.webpack.testing.utils import create_mock_npm_package


class AutoRegistryTestCase(unittest.TestCase):

    def test_autoget(self):
        reg = AutogenWebpackLoaderPluginRegistry('reg')
        with pretty_logging(stream=StringIO()) as s:
            result = reg.get_record('foo')
        self.assertEqual('foo', result.name)
        self.assertIn(
            "AutogenWebpackLoaderPluginRegistry registry 'reg' generated "
            "loader handler 'foo'", s.getvalue(),
        )

    def test_existing(self):
        reg = AutogenWebpackLoaderPluginRegistry('reg')
        reg.records['css'] = loaderplugin.WebpackLoaderHandler(reg, 'css')

        with pretty_logging(stream=StringIO()) as s:
            result = reg.get_record('css')
        self.assertNotIn(
            "AutogenWebpackLoaderPluginRegistry registry 'reg' generated "
            "loader handler 'css'", s.getvalue(),
        )
        self.assertIs(result, reg.records['css'])


class WebpackLoaderPluginTestCase(unittest.TestCase):
    """
    Upstream technically tested some of these, but doing it specifically
    here for posterity (and also for upstream stability purposes).
    """

    def test_unwrap(self):
        f = loaderplugin.WebpackLoaderHandler(None, 'text').unwrap
        self.assertEqual(f('file.txt'), 'file.txt')
        self.assertEqual(f('text!file.txt'), 'file.txt')
        # since there are no nesting...
        self.assertEqual(f('text!file.txt!strip'), 'file.txt!strip')

    def test_unwrap_unstripped_values(self):
        f = loaderplugin.WebpackLoaderHandler(None, 'text').unwrap
        self.assertEqual(f('/file.txt'), '/file.txt')
        self.assertEqual(f('/text!file.txt'), '/text!file.txt')
        self.assertEqual(f('/text!file.txt!strip'), '/text!file.txt!strip')

    def test_unwrap_empty(self):
        f = loaderplugin.WebpackLoaderHandler(None, 'text').unwrap
        # this should be invalid, but we are forgiving
        self.assertEqual(f(''), '')
        self.assertEqual(f('text!'), '')

    def test_call_standard(self):
        srcfile = join(mkdtemp(self), 'some.file.txt')
        spec = Spec(build_dir=mkdtemp(self))
        toolchain = Toolchain()
        with open(srcfile, 'w') as fd:
            fd.write('hello world')

        reg = LoaderPluginRegistry('calmjs.webpack.loaders')
        text = loaderplugin.WebpackLoaderHandler(reg, 'text')
        modpaths, targets, export_module_names = text(
            toolchain, spec,
            'text!some.file.txt', srcfile, 'some.file.txt',
            'text!some.file.txt'
        )

        self.assertEqual(
            {'text!some.file.txt': 'text!some.file.txt'}, modpaths)
        self.assertEqual({
            'some.file.txt': 'some.file.txt',
            './some.file.txt': 'some.file.txt',
        }, targets)
        self.assertEqual(
            ['text!some.file.txt'], export_module_names)

    def test_call_dir_nesting(self):
        srcfile = join(mkdtemp(self), 'some.file.txt')
        tgtfile = join('dir', 'some.file.txt')
        spec = Spec(build_dir=mkdtemp(self))
        toolchain = Toolchain()
        with open(srcfile, 'w') as fd:
            fd.write('hello world')

        reg = LoaderPluginRegistry('calmjs.webpack.loaders')
        text = loaderplugin.WebpackLoaderHandler(reg, 'text')
        modpaths, targets, export_module_names = text(
            toolchain, spec,
            'text!some.file.txt', srcfile, tgtfile, 'text!some.file.txt'
        )

        self.assertTrue(
            exists(join(spec['build_dir'], 'dir', 'some.file.txt')))

        self.assertEqual(
            {'text!some.file.txt': 'text!some.file.txt'}, modpaths)
        self.assertEqual({
            'some.file.txt': tgtfile,
            './some.file.txt': tgtfile,
        }, targets)
        self.assertEqual(
            ['text!some.file.txt'], export_module_names)

    def test_call_loader_chaining(self):
        srcfile = join(mkdtemp(self), 'some.css')
        spec = Spec(build_dir=mkdtemp(self))
        toolchain = Toolchain()
        with open(srcfile, 'w') as fd:
            fd.write('body { color: #000; }')

        reg = LoaderPluginRegistry('calmjs.webpack.loaders')
        reg.records['text'] = text = loaderplugin.WebpackLoaderHandler(
            reg, 'text')
        reg.records['css'] = loaderplugin.WebpackLoaderHandler(reg, 'css')

        modpaths, targets, export_module_names = text(
            toolchain, spec,
            'text!css!some.css', srcfile, 'some.css', 'text!css!some.css'
        )

        self.assertEqual(
            {'text!css!some.css': 'text!css!some.css'}, modpaths)
        self.assertEqual({
            'some.css': 'some.css',
            './some.css': 'some.css',
        }, targets)
        self.assertEqual(
            ['text!css!some.css'], export_module_names)

        self.assertTrue(exists(join(spec['build_dir'], 'some.css')))

    def test_modname_loader_map(self):
        srcfile = join(mkdtemp(self), 'some.css')
        spec = Spec(
            build_dir=mkdtemp(self),
            calmjs_webpack_modname_loader_map={
                'some.css': ['style', 'css']
            },
        )
        toolchain = Toolchain()
        with open(srcfile, 'w') as fd:
            fd.write('.body {}')

        reg = LoaderPluginRegistry('calmjs.webpack.loaders')
        reg.records['style'] = text = loaderplugin.WebpackLoaderHandler(
            reg, 'style')
        reg.records['css'] = loaderplugin.WebpackLoaderHandler(reg, 'css')
        modpaths, targets, export_module_names = text(
            toolchain, spec,
            'style!css!some.css', srcfile, 'some.css', 'style!css!some.css'
        )

        self.assertEqual(
            {'style!css!some.css': 'style!css!some.css'}, modpaths)
        self.assertEqual({
            'some.css': 'some.css',
            './some.css': 'some.css',
        }, targets)
        self.assertEqual(
            [], export_module_names)

    def test_find_node_module_pkg_name(self):
        remember_cwd(self)
        text_handler = loaderplugin.WebpackLoaderHandler(None, 'text')
        working_dir = mkdtemp(self)
        os.chdir(working_dir)
        toolchain = Toolchain()
        spec = Spec()

        # base test without any Node.js packages available
        self.assertEqual(
            'text-loader',
            text_handler.find_node_module_pkg_name(toolchain, spec)
        )

        # now provide a package named simply 'text'
        create_mock_npm_package(working_dir, 'text', 'index.js')
        # which, being available, will resolve directly to 'text' due to
        # ambiguity.
        self.assertEqual(
            'text',
            text_handler.find_node_module_pkg_name(toolchain, spec)
        )

        # however, if a -loader suffixed package (i.e. 'text-loader') is
        # available, the -loader version will be returned instead.
        create_mock_npm_package(working_dir, 'text-loader', 'index.js')
        self.assertEqual(
            'text-loader',
            text_handler.find_node_module_pkg_name(toolchain, spec)
        )

    def test_find_node_module_pkg_name_full_suffix(self):
        remember_cwd(self)
        # this one is fully named 'text-loader'
        text_handler = loaderplugin.WebpackLoaderHandler(None, 'text-loader')
        working_dir = mkdtemp(self)
        os.chdir(working_dir)
        toolchain = Toolchain()
        spec = Spec()

        # base test without any Node.js packages available
        self.assertEqual(
            'text-loader',
            text_handler.find_node_module_pkg_name(toolchain, spec)
        )

        # not affected by a prefix-free package
        create_mock_npm_package(working_dir, 'text', 'index.js')
        self.assertEqual(
            'text-loader',
            text_handler.find_node_module_pkg_name(toolchain, spec)
        )


class WebpackModuleLoaderRegistryTestCase(unittest.TestCase):

    def test_module_loader_registry_multiple_loaders(self):
        working_set = WorkingSet({
            'calmjs.module': [
                'module4 = calmjs.testing.module4',
            ],
            'calmjs.module.webpackloader': [
                'style!css = css[css]',
                'json = json[json]',
            ],
            __name__: [
                'calmjs.module = calmjs.module:ModuleRegistry',
                'calmjs.module.webpackloader = '
                'calmjs.webpack.loaderplugin:WebpackModuleLoaderRegistry',
            ]},
            # use a real distribution instead for this case
            dist=root_working_set.find(Requirement.parse('calmjs')),
        )

        registry = ModuleRegistry('calmjs.module', _working_set=working_set)
        loader_registry = WebpackModuleLoaderRegistry(
            'calmjs.module.webpackloader',
            _working_set=working_set, _parent=registry)
        self.assertEqual({
            'calmjs': ['calmjs.testing.module4'],
        }, loader_registry.package_module_map)

        self.assertEqual(
            ['json', 'style!css'],
            sorted(loader_registry.get_loaders_for_package('calmjs'))
        )

        self.assertEqual([
            WebpackModuleLoaderRegistryKey(
                loader='json', modname='calmjs/testing/module4/data.json'),
            WebpackModuleLoaderRegistryKey(
                loader='style!css',
                modname='calmjs/testing/module4/other.css'),
        ], sorted(loader_registry.get_records_for_package('calmjs').keys()))


class PluginLoaderUtilityTestCase(unittest.TestCase):

    def test_normalize_and_register_webpackloaders(self):
        sourcepath_map = {
            'normal/module': '/path/to/normal/module.js',
            'text!prefixed/resource.txt': '/path/to/prefixed/resource.txt',
            WebpackModuleLoaderRegistryKey('style!css', 'some/style.css'):
                '/path/to/some/style.css',
        }
        spec = Spec()
        self.assertEqual({
            'normal/module': '/path/to/normal/module.js',
            'text!prefixed/resource.txt': '/path/to/prefixed/resource.txt',
            'style!css!some/style.css': '/path/to/some/style.css',
        }, normalize_and_register_webpackloaders(spec, sourcepath_map))
        self.assertEqual({
            'some/style.css': ['style', 'css'],
        }, spec['calmjs_webpack_modname_loader_map'])

    def test_normalize_and_register_webpackloaders_empty(self):
        sourcepath_map = {}
        spec = Spec()
        self.assertEqual(
            {}, normalize_and_register_webpackloaders(spec, sourcepath_map))
        self.assertEqual({}, spec['calmjs_webpack_modname_loader_map'])

    def test_update_spec_webpack_loaders_modules(self):
        spec = Spec(
            calmjs_webpack_modname_loader_map={
                'some/style.css': ['style', 'css'],
            },
        )
        alias = {
            'some/style.css': '/path/to/some/style.css',
        }
        update_spec_webpack_loaders_modules(spec, alias)

        self.assertEqual([{
            'test': '/path/to/some/style.css',
            'loaders': ['style', 'css'],
        }], spec['webpack_module_rules'])

    def test_update_spec_webpack_loaders_modules_missing_alias(self):
        spec = Spec(
            calmjs_webpack_modname_loader_map={
                'some/style.css': ['style', 'css'],
            },
        )
        alias = {}
        with pretty_logging(stream=StringIO()) as s:
            update_spec_webpack_loaders_modules(spec, alias)

        self.assertIn(
            "WARNING modname 'some/style.css' requires loader chain "
            "['style', 'css'] but it does not have a corresponding webpack "
            "resolve.alias; webpack build failure may result as loaders are "
            "not configured for this modname", s.getvalue(),
        )

        self.assertEqual([], spec['webpack_module_rules'])

    def test_update_spec_webpack_loaders_modules_empty(self):
        spec = Spec()
        alias = {}
        update_spec_webpack_loaders_modules(spec, alias)
        self.assertEqual([], spec['webpack_module_rules'])
