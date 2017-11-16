# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import unittest
import textwrap
import json
from io import StringIO

from calmjs.parse import io
from calmjs.parse.parsers.es5 import parse as es5
from calmjs.parse.unparsers.es5 import pretty_print

from calmjs.webpack.manipulation import create_calmjs_require
from calmjs.webpack.manipulation import extract_dynamic_require
from calmjs.webpack.manipulation import convert_dynamic_require
from calmjs.webpack.manipulation import convert_dynamic_require_unparser


def parse_first_expr(src):
    return es5(src).children()[0].expr


class ExtractionTestCase(unittest.TestCase):
    """
    Test out the extraction helper functions
    """

    def test_probe_commonjs_static(self):
        source = textwrap.dedent("""
        var example1 = require('example1');
        var example2 = require("example2");
        """).lstrip()

        self.assertEqual(len(list(extract_dynamic_require(es5(source)))), 0)

    def test_probe_amd_static(self):
        source = textwrap.dedent("""
        require(['example1', "example2"], function(example1, example2) {
        });
        """).lstrip()

        self.assertEqual(len(list(extract_dynamic_require(es5(source)))), 0)

    def test_probe_commonjs_dynamic(self):
        source = textwrap.dedent("""
        var example1 = require('example1');
        var example2 = require(example1.value);
        var example3 = require(exampl2.parent + '/index');
        """).lstrip()

        self.assertEqual(len(list(extract_dynamic_require(es5(source)))), 2)

    def test_probe_amd_dynamic(self):
        source = textwrap.dedent("""
        var source = "example.package"
        require(['root', source + '/index', source], function(root, idx) {
        });
        require(['root'], function(root) {
        });
        require([source], function(source) {
        });
        """).lstrip()
        self.assertEqual(len(list(extract_dynamic_require(es5(source)))), 2)

    def test_probe_other_access_types(self):
        source = textwrap.dedent("""
        __calmjs_loader__.require(value);
        require('__calmjs_loader__').require(value);
        """).lstrip()

        # none of these should have been extracted
        self.assertEqual(len(list(extract_dynamic_require(es5(source)))), 0)


class CreationTestCase(unittest.TestCase):
    """
    Node creation test cases.
    """

    # using pretty_print simply because the dynamically constructed
    # node is of the generic base type, without the str/repr attached.

    def test_create_calmjs_require_static(self):
        # no restrictions on conversion static imports when called
        # directly
        node = parse_first_expr("require('static');")
        self.assertEqual(
            pretty_print(create_calmjs_require(node)),
            "require('__calmjs_loader__').require('static')",
        )

    def test_create_calmjs_require_dynamic(self):
        node = parse_first_expr("require(dynamic);")
        self.assertEqual(
            pretty_print(create_calmjs_require(node)),
            "require('__calmjs_loader__').require(dynamic)",
        )

    def test_create_calmjs_require_nested_require(self):
        # remember, this only generates a new node; see test on the
        # fully assembled function.
        node = parse_first_expr("require(require(dynamic));")
        self.assertEqual(
            pretty_print(create_calmjs_require(node)),
            "require('__calmjs_loader__').require(require(dynamic))",
        )


class ConversionTestCase(unittest.TestCase):
    """
    Node conversion test cases.
    """

    def test_convert_calmjs_require_empty(self):
        node = es5("require();")
        # should be unchanged.
        self.assertEqual(
            pretty_print(convert_dynamic_require(node)),
            "require();\n",
        )

    def test_convert_calmjs_require_static(self):
        node = es5("require('static');")
        # should be unchanged.
        self.assertEqual(
            pretty_print(convert_dynamic_require(node)),
            "require('static');\n",
        )

    def test_create_calmjs_require_dynamic(self):
        # should be modified.
        node = es5("require(dynamic);")
        self.assertEqual(
            pretty_print(convert_dynamic_require(node)),
            "require('__calmjs_loader__').require(dynamic);\n",
        )

    def test_create_calmjs_require_nested_require(self):
        # nested one should be converted.
        node = es5("require(require(dynamic));")
        self.assertEqual(
            pretty_print(convert_dynamic_require(node)),
            "require('__calmjs_loader__').require("
            "require('__calmjs_loader__').require(dynamic));\n",
        )

    def test_dynamic_commonjs_in_static_amd(self):
        # nested one should be converted.
        node = es5("""
        require(['jQuery', 'underscore'], function($, _) {
          var dynamic_module = require(dynamic);
        });
        """)
        self.assertEqual(textwrap.dedent("""
        require(['jQuery', 'underscore'], function($, _) {
          var dynamic_module = require('__calmjs_loader__').require(dynamic);
        });
        """).lstrip(), pretty_print(convert_dynamic_require(node)))

    def test_dynamic_commonjs_in_dynamic_amd(self):
        node = es5("""
        require([dynamic], function(module) {
          var redefined = require(dynamic);
        });
        """)
        self.assertEqual(textwrap.dedent("""
        require('__calmjs_loader__').require([dynamic], function(module) {
          var redefined = require('__calmjs_loader__').require(dynamic);
        });
        """).lstrip(), pretty_print(convert_dynamic_require(node)))


class UnparserTestCase(unittest.TestCase):
    """
    Using the unparser version.
    """

    def readwrite(self, source):
        unparser = convert_dynamic_require_unparser()
        original = StringIO(source)
        original.name = 'source.js'
        output = StringIO()
        output.name = 'output.js'
        srcmap = StringIO()
        srcmap.name = 'output.js.map'
        io.write(unparser, io.read(es5, original), output, srcmap)
        return output, srcmap

    def test_convert_calmjs_require_static(self):
        output, srcmap = self.readwrite("require('static');")
        # should be unchanged.
        self.assertEqual(textwrap.dedent("""
        require('static');

        //# sourceMappingURL=output.js.map
        """).lstrip(), output.getvalue())
        self.assertEqual({
            'file': 'output.js',
            'mappings': 'AAAA;',
            'names': [],
            'sources': ['source.js'],
            'version': 3,
        }, json.loads(srcmap.getvalue()))

    def test_convert_calmjs_require_dynamic(self):
        output, srcmap = self.readwrite("require(dynamic);")
        # should be modified.
        self.assertEqual(textwrap.dedent("""
        require('__calmjs_loader__').require(dynamic);

        //# sourceMappingURL=output.js.map
        """).lstrip(), output.getvalue())
        self.assertEqual({
            'file': 'output.js',
            'mappings': '6BAAA;',
            'names': [],
            'sources': ['source.js'],
            'version': 3,
        }, json.loads(srcmap.getvalue()))

    def test_dynamic_commonjs_in_static_amd(self):
        output, srcmap = self.readwrite(textwrap.dedent("""
        require(['jQuery', 'underscore'], function($, _) {
            var dynamic_module = require(dynamic);
        });
        """).lstrip())
        self.assertEqual(textwrap.dedent("""
        require(['jQuery', 'underscore'], function($, _) {
            var dynamic_module = require('__calmjs_loader__').require(dynamic);
        });

        //# sourceMappingURL=output.js.map
        """).lstrip(), output.getvalue())
        self.assertEqual({
            'file': 'output.js',
            'mappings': 'AAAA;IACI,qB,6BAAqB;AACzB;',
            'names': [],
            'sources': ['source.js'],
            'version': 3,
        }, json.loads(srcmap.getvalue()))
