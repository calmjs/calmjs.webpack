# -*- coding: utf-8 -*-
import unittest
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

from calmjs.toolchain import Spec
from calmjs.toolchain import Toolchain
from calmjs.utils import pretty_logging
from calmjs.testing.utils import mkdtemp
from calmjs.testing.mocks import StringIO
from calmjs.testing.mocks import WorkingSet


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
