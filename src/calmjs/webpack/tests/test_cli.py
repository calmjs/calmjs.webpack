# -*- coding: utf-8 -*-
import unittest

from calmjs.toolchain import Spec
from calmjs.utils import pretty_logging

from calmjs.webpack.cli import create_spec
from calmjs.webpack.cli import compile_all

from calmjs.testing.mocks import StringIO


class CliTestCase(unittest.TestCase):
    """
    Test mostly basic implementation, most of the core test will be done
    in the toolchain and/or the integration tests.
    """

    def test_create_spec_empty(self):
        with pretty_logging(stream=StringIO()) as stream:
            spec = create_spec([])

        self.assertNotIn('packages []', stream.getvalue())
        self.assertIn('no packages specified', stream.getvalue())
        self.assertIn(
            "using calmjs bootstrap; webpack.output.library set to "
            "'__calmjs__'", stream.getvalue()
        )
        self.assertTrue(isinstance(spec, Spec))
        self.assertEqual(spec['export_target'], 'calmjs.webpack.export.js')
        self.assertEqual(spec['calmjs_module_registry_names'], [])
        self.assertIn('webpack_externals', spec)
        self.assertEqual(spec['webpack_output_library'], '__calmjs__')

    def test_create_spec_empty_calmjs_compat_disable(self):
        with pretty_logging(stream=StringIO()) as stream:
            spec = create_spec([], calmjs_compat=False)

        self.assertNotIn('packages []', stream.getvalue())
        self.assertIn('no packages specified', stream.getvalue())
        self.assertIn(
            "calmjs_compat is disabled; webpack.output.library automatically "
            "set to 'calmjs.webpack.export', derived from input package names "
            "and export filename as the entry point is defined to be the "
            "simplified calmjs bootstrap.", stream.getvalue()
        )
        self.assertTrue(isinstance(spec, Spec))
        self.assertNotIn('webpack_externals', spec)
        self.assertEqual(
            spec['webpack_output_library'], 'calmjs.webpack.export')

    def test_create_spec_with_calmjs_webpack(self):
        with pretty_logging(stream=StringIO()) as stream:
            spec = create_spec(['calmjs.webpack'])
        self.assertTrue(isinstance(spec, Spec))
        self.assertEqual(spec['export_target'], 'calmjs.webpack.js')
        self.assertEqual(spec.get('webpack_entry_point'), '__calmjs__')
        self.assertEqual(
            spec['calmjs_module_registry_names'], ['calmjs.module'])
        self.assertEqual(
            spec['source_package_names'], ['calmjs.webpack'])

        log = stream.getvalue()
        self.assertIn(
            "automatically picked registries ['calmjs.module'] for "
            "building source map", log,
        )

    def test_create_spec_with_calmjs_webpack_entry_point_warning(self):
        with pretty_logging(stream=StringIO()) as stream:
            spec = create_spec(['calmjs.webpack'], webpack_entry_point='entry')
        self.assertTrue(isinstance(spec, Spec))
        self.assertEqual(spec['export_target'], 'calmjs.webpack.js')
        self.assertEqual(spec.get('webpack_entry_point'), 'entry')
        self.assertEqual(
            spec['calmjs_module_registry_names'], ['calmjs.module'])
        self.assertEqual(
            spec['source_package_names'], ['calmjs.webpack'])

        log = stream.getvalue()
        self.assertIn(
            "webpack_entry_point and/or webpack_output_library is assigned "
            "a different value than their defaults while calmjs_compat is set "
            "to True ", log
        )

    def test_create_spec_with_calmjs_webpack_output_library_warning(self):
        with pretty_logging(stream=StringIO()) as stream:
            create_spec(['calmjs.webpack'], webpack_output_library='entry')
        log = stream.getvalue()
        self.assertIn(
            "webpack_entry_point and/or webpack_output_library is assigned "
            "a different value than their defaults while calmjs_compat is set "
            "to True ", log
        )

    def test_create_spec_with_calmjs_webpack_no_bootstrap(self):
        with pretty_logging(stream=StringIO()) as stream:
            spec = create_spec(['calmjs.webpack'], calmjs_compat=False)
        self.assertTrue(isinstance(spec, Spec))
        self.assertEqual(spec['export_target'], 'calmjs.webpack.js')
        self.assertEqual(
            spec['calmjs_module_registry_names'], ['calmjs.module'])
        self.assertEqual(
            spec['source_package_names'], ['calmjs.webpack'])

        log = stream.getvalue()
        self.assertIn(
            "automatically picked registries ['calmjs.module'] for "
            "building source map", log,
        )
        self.assertEqual(spec.get('webpack_entry_point'), '__calmjs__')
        self.assertEqual(
            spec['webpack_output_library'], 'calmjs.webpack')

    def test_create_spec_with_calmjs_webpack_no_registry(self):
        with pretty_logging(stream=StringIO()) as stream:
            spec = create_spec(
                ['calmjs.webpack'], source_registry_method='none')
        self.assertTrue(isinstance(spec, Spec))
        self.assertEqual(spec['export_target'], 'calmjs.webpack.js')
        self.assertEqual(
            spec['calmjs_module_registry_names'], [])
        self.assertEqual(
            spec['source_package_names'], ['calmjs.webpack'])

        log = stream.getvalue()
        self.assertIn(
            "no module registry declarations found using packages "
            "['calmjs.webpack'] using acquisition method 'none'", log
        )

    def test_create_spec_with_calmjs_webpack_manual_source(self):
        with pretty_logging(stream=StringIO()) as stream:
            spec = create_spec(
                ['calmjs.webpack'], source_registries=['calmjs.module.tests'])
        self.assertTrue(isinstance(spec, Spec))
        self.assertEqual(spec['export_target'], 'calmjs.webpack.js')
        self.assertEqual(
            spec['calmjs_module_registry_names'], ['calmjs.module.tests'])
        self.assertEqual(
            spec['source_package_names'], ['calmjs.webpack'])

        log = stream.getvalue()
        self.assertIn(
            "using manually specified registries ['calmjs.module.tests'] for "
            "building source map", log,
        )

    def test_create_spec_with_calmjs_webpack_entry_point_no_compat(self):
        with pretty_logging(stream=StringIO()) as stream:
            spec = create_spec(
                ['calmjs.webpack'], calmjs_compat=False,
                webpack_entry_point='custom_webpack',
            )
        log = stream.getvalue()
        self.assertNotIn(
            "webpack_entry_point is ignored; set calmjs_compat to false "
            "to enable manual webpack.entry specification",  log
        )
        self.assertIn(
            "calmjs_compat is disabled; webpack.output.library automatically "
            "set to 'custom_webpack' as this is the explicit webpack entry "
            "point specified", log
        )
        self.assertEqual(spec['webpack_entry_point'], 'custom_webpack')
        self.assertEqual(spec.get('webpack_output_library'), 'custom_webpack')

    def test_create_spec_with_calmjs_webpack_output_library_no_compat(self):
        with pretty_logging(stream=StringIO()) as stream:
            spec = create_spec(
                ['calmjs.webpack'], calmjs_compat=False,
                webpack_entry_point='custom_entry',
                webpack_output_library='custom_library',
            )
        log = stream.getvalue()
        self.assertNotIn(
            "webpack_entry_point is ignored; set calmjs_compat to false "
            "to enable manual webpack.entry specification", log
        )
        self.assertIn(
            "webpack.output.library is manually set to 'custom_library'", log)
        self.assertEqual(spec['webpack_entry_point'], 'custom_entry')
        self.assertEqual(spec['webpack_output_library'], 'custom_library')

    def test_create_spec_with_calmjs_webpack_output_library_disable(self):
        with pretty_logging(stream=StringIO()) as stream:
            spec = create_spec(
                ['calmjs.webpack'], calmjs_compat=False,
                webpack_entry_point='custom_entry',
                webpack_output_library=False,
            )
        log = stream.getvalue()
        self.assertNotIn(
            "webpack_entry_point is ignored; set calmjs_compat to false "
            "to enable manual webpack.entry specification", log
        )
        self.assertIn(
            "webpack.output.library is disabled; it will be unset.", log)
        self.assertEqual(spec['webpack_entry_point'], 'custom_entry')
        self.assertNotIn('webpack_output_library', spec)

    def test_toolchain_empty(self):
        # dict works well enough as a null toolchain
        with pretty_logging(stream=StringIO()) as stream:
            spec = compile_all([], toolchain=dict)

        self.assertNotIn('packages []', stream.getvalue())
        self.assertIn('no packages specified', stream.getvalue())
        self.assertTrue(isinstance(spec, Spec))
        self.assertEqual(spec['export_target'], 'calmjs.webpack.export.js')
