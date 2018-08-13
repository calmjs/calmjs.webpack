# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import unittest
from textwrap import dedent

from calmjs.parse import asttypes
from calmjs.webpack import configuration


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

        exported = plugins.export()
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
