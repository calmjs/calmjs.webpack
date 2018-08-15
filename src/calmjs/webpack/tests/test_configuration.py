# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import unittest
from textwrap import dedent

from calmjs.parse import asttypes
from calmjs.webpack import configuration

from calmjs.utils import pretty_logging
from calmjs.testing.mocks import StringIO


class CleanConfigTestCase(unittest.TestCase):

    def test_version_2(self):
        config = {}
        configuration.clean_config(config, '2.6.1')
        self.assertEqual({}, config)
        config = {'mode': 'none'}
        configuration.clean_config(config, '2.6.1')
        self.assertEqual({}, config)

    def test_version_4(self):
        config = {'mode': 'none'}
        configuration.clean_config(config, '4.0.1')
        self.assertEqual({'mode': 'none'}, config)
        config = {}
        configuration.clean_config(config, '4.0.1')
        self.assertEqual({'mode': 'none'}, config)


class ConfigBaseTestCase(unittest.TestCase):

    def test_base_config(self):
        config = configuration.ConfigMapping()
        self.assertEqual(config, {})
        config['foo'] = 'bar'
        self.assertEqual(config, {'foo': 'bar'})
        self.assertEqual(config.json(), '{"foo": "bar"}')
        self.assertEqual(str(config.es5()), '{\n    "foo": "bar"\n}')

    def test_mapping_shallow_clone(self):
        config = configuration.ConfigMapping()
        # instance based manipulation of the special mapping is possible
        # but really shouldn't be done when used as a real process.
        config._special_mapping = {'bar': configuration.ConfigMapping}

        foo = configuration.ConfigMapping()
        config['foo'] = foo
        self.assertIs(config['foo'], foo)
        # this would not be the case as the special mapping triggers a
        # clone on assignment.
        bar = configuration.ConfigMapping()
        config['bar'] = bar
        self.assertIsNot(config['bar'], bar)
        self.assertTrue(isinstance(config['bar'], configuration.ConfigMapping))


class PluginsObjectTestCase(unittest.TestCase):

    def test_plugins(self):
        plugins = configuration._WebpackConfigPlugins()
        plugins.append('new webpack.plugin.DummyPlugin1({})')
        self.assertTrue(isinstance(plugins[0], asttypes.Node))

        plugins.append('new webpack.plugin.DummyPlugin2({})')
        self.assertEqual(dedent("""
        [
            new webpack.plugin.DummyPlugin1({}),
            new webpack.plugin.DummyPlugin2({})
        ]
        """).strip(), str(plugins))

        exported = plugins.es5()
        self.assertTrue(isinstance(exported, asttypes.Node))

        for plugin, export in zip(plugins, exported):
            self.assertTrue(isinstance(plugin, asttypes.Node))
            self.assertEqual(plugin, export)

        self.assertEqual(2, len(exported.items))

        del plugins[0]
        self.assertEqual(dedent("""
        [
            new webpack.plugin.DummyPlugin2({})
        ]
        """).strip(), str(plugins))

        # exported node should not change.
        self.assertEqual(2, len(exported.items))
        self.assertEqual(1, len(plugins))

        plugins[0] = 'new customplugin.Demo({config: true})'
        self.assertEqual(dedent("""
        [
            new customplugin.Demo({
                config: true
            })
        ]
        """).strip(), str(plugins))

    def test_plugins_defaults(self):
        plugins = configuration._WebpackConfigPlugins([
            'new Plugin1({})',
            'new Plugin2({})',
        ])
        self.assertEqual(dedent("""
        [
            new Plugin1({}),
            new Plugin2({})
        ]
        """).strip(), str(plugins))


class ConfigObjectTestCase(unittest.TestCase):

    def test_base_config(self):
        config = configuration.WebpackConfig()
        self.assertEqual(config, {})
        config['foo'] = 'bar'
        self.assertEqual(config, {'foo': 'bar'})
        self.assertEqual(dedent("""
        'use strict';
        var webpack = require('webpack');
        var webpackConfig = {
            "foo": "bar"
        };
        module.exports = webpackConfig;
        """).lstrip(), str(config))
        self.assertEqual(1, len(config))
        self.assertNotIn('plugins', config)

        del config['foo']
        self.assertEqual(config, {})
        self.assertEqual(dedent("""
        'use strict';
        var webpack = require('webpack');
        var webpackConfig = {};
        module.exports = webpackConfig;
        """).lstrip(), str(config))

    def test_defined_special_keys_filtered(self):
        config = configuration.WebpackConfig(__webpack_target__=(1, 2, 3))
        self.assertEqual(config, {'__webpack_target__': (1, 2, 3)})
        self.assertEqual(dedent("""
        'use strict';
        var webpack = require('webpack');
        var webpackConfig = {};
        module.exports = webpackConfig;
        """).lstrip(), str(config))

    def test_base_config_plugins(self):
        config = configuration.WebpackConfig({
            'mode': 'production',
            'plugins': [
                'new webpack.optimize.UglifyJsPlugin({})',
            ],
        })
        self.assertEqual(2, len(config))
        self.assertIn('plugins', config)
        self.assertEqual(dedent("""
        'use strict';
        var webpack = require('webpack');
        var webpackConfig = {
            "mode": "production",
            "plugins": [
                new webpack.optimize.UglifyJsPlugin({})
            ]
        };
        module.exports = webpackConfig;
        """).lstrip(), str(config))

        config['plugins'].append('new webpack.demo.Plugin({})')
        self.assertEqual(dedent("""
        'use strict';
        var webpack = require('webpack');
        var webpackConfig = {
            "mode": "production",
            "plugins": [
                new webpack.optimize.UglifyJsPlugin({}),
                new webpack.demo.Plugin({})
            ]
        };
        module.exports = webpackConfig;
        """).lstrip(), str(config))

    def test_export_config_mode_versions(self):
        config = configuration.WebpackConfig(
            mode='none',
        )
        self.assertIn('"mode": "none"', str(config))

        # downgrade webpack version
        config['__webpack_target__'] = (2, 6, 1)
        with pretty_logging(stream=StringIO()) as fd:
            # default mode value should not be seralized
            config_str = str(config)
            self.assertNotIn('"mode": "none"', config_str)
            self.assertIn("var webpackConfig = {}", config_str)
        self.assertIn(
            'INFO calmjs.webpack.configuration unsupported property with '
            'default value removed for webpack 2.6.1: {"mode": "none"}',
            fd.getvalue()
        )

        # change mode to a non-default value
        config['mode'] = 'production'
        with pretty_logging(stream=StringIO()) as fd:
            # default mode value should not be seralized
            config_str = str(config)
            self.assertNotIn('"mode": "production"', config_str)
            self.assertIn("var webpackConfig = {}", config_str)
        self.assertIn(
            'WARNING calmjs.webpack.configuration unsupported property with '
            'non-default value removed for webpack 2.6.1: '
            '{"mode": "production"}',
            fd.getvalue()
        )

    def test_export_config_rules(self):
        config = configuration.WebpackConfig(
            module={
                "rules": [],
            },
        )
        # the disabling rule gets injected
        with pretty_logging(stream=StringIO()) as fd:
            self.assertIn('type: "javascript/auto"', str(config))
        self.assertIn(
            'INFO calmjs.webpack.configuration disabling default json '
            'loader module rule for webpack 4.0.0', fd.getvalue()
        )

        # downgrade webpack version
        config['__webpack_target__'] = (2, 6, 1)
        with pretty_logging(logger='calmjs.webpack', stream=StringIO()) as fd:
            self.assertNotIn('type: "javascript/auto"', str(config))

        self.assertEqual('', fd.getvalue())

    def test_export_config_optimization(self):
        config = configuration.WebpackConfig(
            optimization={"minimize": True},
        )
        # standard optimization setting is kept for latest webpack
        with pretty_logging(logger='calmjs.webpack', stream=StringIO()) as fd:
            config_s = str(config)
            self.assertIn('"optimization": {', config_s)
            self.assertIn('"minimize": true', config_s)

        self.assertEqual('', fd.getvalue())

        # downgrade webpack version
        config['__webpack_target__'] = (2, 6, 1)
        with pretty_logging(logger='calmjs.webpack', stream=StringIO()) as fd:
            config_s = str(config)
            self.assertNotIn('"optimization": {', config_s)
            self.assertNotIn('"minimize": true', config_s)
            self.assertIn('"plugins": [', config_s)
            self.assertIn('new webpack.optimize.UglifyJsPlugin({})', config_s)

        self.assertIn(
            "converting unsupported property to a plugin for "
            "webpack 2.6.1: {", fd.getvalue())
        self.assertIn('"minimize": true', fd.getvalue())

        # set minimize to false
        config['optimization']["minimize"] = False
        with pretty_logging(logger='calmjs.webpack', stream=StringIO()) as fd:
            config_s = str(config)
            self.assertNotIn('"optimization": {', config_s)
            self.assertNotIn('"minimize": true', config_s)
            self.assertNotIn('"plugins": [', config_s)

        self.assertIn(
            "dropping unsupported property for webpack 2.6.1: {",
            fd.getvalue())
        self.assertIn('"minimize": false', fd.getvalue())

        # set minimize to an unsupported value
        config['optimization']["minimize"] = {}
        with pretty_logging(logger='calmjs.webpack', stream=StringIO()) as fd:
            config_s = str(config)
            self.assertNotIn('"optimization": {', config_s)
            self.assertNotIn('"minimize": true', config_s)
            self.assertNotIn('"plugins": [', config_s)

        self.assertIn(
            "dropping unsupported property for webpack 2.6.1: {",
            fd.getvalue())
        self.assertIn('"minimize": {}', fd.getvalue())
