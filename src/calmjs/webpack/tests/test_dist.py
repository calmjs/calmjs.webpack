# -*- coding: utf-8 -*-
import unittest
from os.path import join
from calmjs.utils import pretty_logging
from calmjs.webpack import dist

from calmjs.testing import utils
from calmjs.testing.mocks import StringIO


class BaseDistTestCase(unittest.TestCase):
    """
    Test out dist functions
    """

    def test_acquire_method(self):
        foo = object()
        bar = object()
        r = dist.acquire_method({'foo': foo, 'bar': bar}, 'foo', default='bar')
        self.assertIs(r, foo)
        r = dist.acquire_method({'foo': foo, 'bar': bar}, 'wat', default='bar')
        self.assertIs(r, bar)


class DistIntegrationTestCase(unittest.TestCase):
    """
    A number of integration tests, using mocked up data created with the
    calmjs.testing helpers.
    """

    @classmethod
    def setUpClass(cls):
        utils.setup_class_integration_environment(cls)

    @classmethod
    def tearDownClass(cls):
        utils.teardown_class_integration_environment(cls)

    # test the generate_transpile call as pairs.
    def test_generate_transpile_explicit_registry_none(self):
        self.assertEqual([
        ], sorted(dist.generate_transpile_sourcepaths(
            ['site'], registries=(self.registry_name,), method='none')))

        self.assertEqual([
        ], sorted(dist.generate_transpiled_externals(
            ['site'], registries=(self.registry_name,), method='none')))

    def test_generate_transpile_explicit_registry_default(self):
        self.assertEqual([
            'forms/ui', 'framework/lib', 'widget/core', 'widget/datepicker',
            'widget/richedit',
        ], sorted(dist.generate_transpile_sourcepaths(
            ['site'], registries=(self.registry_name,))))

        self.assertEqual([
        ], sorted(dist.generate_transpiled_externals(
            ['site'], registries=(self.registry_name,))))

    def test_generate_transpile_sourcepaths_explicit_registry_auto(self):
        # site will have nothing, but all the transpiled externals will
        # be listed.
        self.assertEqual([
        ], sorted(dist.generate_transpile_sourcepaths(
            ['site'], registries=(self.registry_name,), method='explicit')))

        self.assertEqual([
            'forms/ui', 'framework/lib', 'widget/core', 'widget/datepicker',
            'widget/richedit',
        ], sorted(dist.generate_transpiled_externals(
            ['site'], registries=(self.registry_name,), method='explicit')))

        # forms package will have forms/ui explicitly stated, but the
        # others will be marked as externals
        self.assertEqual([
            'forms/ui',
        ], sorted(dist.generate_transpile_sourcepaths(
            ['forms'], registries=(self.registry_name,), method='explicit')))

        self.assertEqual([
            'framework/lib', 'widget/core', 'widget/datepicker',
            'widget/richedit',
        ], sorted(dist.generate_transpiled_externals(
            ['forms'], registries=(self.registry_name,), method='explicit')))

    def test_generate_transpile_sourcepaths_service_default(self):
        self.assertEqual([
            'framework/lib', 'service/endpoint', 'service/rpc/lib',
        ], sorted(dist.generate_transpile_sourcepaths(
            ['service'], registries=(self.registry_name,))))

        self.assertEqual([
        ], sorted(dist.generate_transpiled_externals(
            ['site'], registries=(self.registry_name,))))

    def test_generate_transpile_sourcepaths_service_explicit(self):
        self.assertEqual([
            'service/endpoint', 'service/rpc/lib',
        ], sorted(dist.generate_transpile_sourcepaths(
            ['service'], registries=(self.registry_name,), method='explicit')))

        self.assertEqual({
            'framework/lib': {
                "root": ["__calmjs__", "modules", "framework/lib"],
                "amd": ["__calmjs__", "modules", "framework/lib"],
                "commonjs": [
                    "global", "__calmjs__", "modules", "framework/lib"],
                "commonjs2": [
                    "global", "__calmjs__", "modules", "framework/lib"],
            },
        }, dist.generate_transpiled_externals(
            ['service'], registries=(self.registry_name,), method='explicit'))

    def test_get_calmjs_module_registry_for_site_no_registry(self):
        # since site doesn't actually define an explicit registry that
        # it needs.
        self.assertEqual(
            dist.get_calmjs_module_registry_for(['site'], method='explicit'),
            [],
        )

        self.assertEqual(
            dist.get_calmjs_module_registry_for(['site'], method='all'),
            [self.registry_name],
        )

        self.assertEqual(
            dist.get_calmjs_module_registry_for(['site'], method='none'),
            [],
        )

    def test_get_calmjs_module_registry_for_explicit_get(self):
        self.assertEqual(
            dist.get_calmjs_module_registry_for(
                ['calmjs.simulated'], method='explicit'),
            [self.registry_name],
        )

        self.assertEqual(
            dist.get_calmjs_module_registry_for(['forms'], method='auto'),
            [self.registry_name],
        )

    def test_generate_bundle_sourcepaths_none(self):
        mapping = dist.generate_bundle_sourcepaths(
            ['site'], method='none')
        self.assertEqual(sorted(mapping.keys()), [])

    def test_generate_bundle_sourcepaths_bad_dir(self):
        bad_dir = utils.mkdtemp(self)
        with pretty_logging(stream=StringIO()) as log:
            mapping = dist.generate_bundle_sourcepaths(
                ['service'], bad_dir)
        self.assertEqual(sorted(mapping.keys()), [])
        self.assertIn('fake_modules', log.getvalue())

    def test_generate_bundle_sourcepaths_site_default(self):
        mapping = dist.generate_bundle_sourcepaths(
            ['site'], self.dist_dir)
        self.assertEqual(sorted(mapping.keys()), ['jquery', 'underscore'])
        self.assertTrue(mapping['jquery'].endswith(
            join('fake_modules', 'jquery', 'dist', 'jquery.js')))
        self.assertTrue(mapping['underscore'].endswith(
            join('fake_modules', 'underscore', 'underscore.js')))

    def test_generate_bundle_sourcepaths_default(self):
        mapping = dist.generate_bundle_sourcepaths(
            ['framework'], self.dist_dir)
        self.assertEqual(sorted(mapping.keys()), [
            'jquery', 'underscore',
        ])
        self.assertIn(
            (join('underscore', 'underscore-min.js')), mapping['underscore'])
        mapping = dist.generate_bundle_sourcepaths(
            ['service'], self.dist_dir)
        self.assertEqual(sorted(mapping.keys()), [
            'jquery', 'underscore',
        ])
        self.assertIn(
            (join('underscore', 'underscore.js')), mapping['underscore'])
        self.assertIn('jquery', mapping['jquery'])

    def test_generate_bundle_sourcepaths_service_explicit(self):
        mapping = dist.generate_bundle_sourcepaths(
            ['service'], self.dist_dir, method='explicit')
        self.assertEqual(sorted(mapping.keys()), ['underscore'])
        self.assertIn(
            (join('underscore', 'underscore.js')), mapping['underscore'])

        externals = dist.generate_bundled_externals(
            ['service'], self.dist_dir, method='explicit')
        self.assertEqual(externals, {
            'jquery': {
                "root": 'jquery', "amd": 'jquery',
                'commonjs': 'jquery', 'commonjs2': 'jquery',
            }
        })
