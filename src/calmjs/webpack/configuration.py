# -*- coding: utf-8 -*-
"""
Various utility functions
"""

from collections import MutableMapping
from collections import MutableSequence
from json import dumps
from operator import (
    lt,
    ge,
)

from calmjs.parse.factory import AstTypesFactory
from calmjs.parse.parsers.es5 import Parser
from calmjs.parse.rules import indent
from calmjs.parse.ruletypes import (
    Text,
    Indent,
    Newline,
    ElisionJoinAttr,
    Dedent,
    OptionalNewline,
)
from calmjs.parse.unparsers.es5 import definitions
from calmjs.parse.unparsers.es5 import Unparser
from calmjs.parse.walkers import ReprWalker

from calmjs.webpack.base import DEFAULT_WEBPACK_MODE
from calmjs.webpack.interrogation import walker

config_definitions = dict(**definitions)
config_definitions.update({
    # definition to ensure that array items are serialized one per line
    'Array': (
        Text(value='['),
        Indent, Newline,
        ElisionJoinAttr('items', value=(Newline,)),
        Dedent, OptionalNewline,
        Text(value=']'),
    ),
})
wpconf_serializer = Unparser(
    definitions=config_definitions,
    rules=(indent(indent_str='    '),),
)

# produce customized versions of the commented calmjs.parse imports
# from calmjs.parse import asttypes
asttypes = AstTypesFactory(
    lambda ast: ''.join(chunk.text for chunk in wpconf_serializer(ast)),
    ReprWalker(),
)


# from calmjs.parse import es5
def es5(source):
    return Parser(asttypes=asttypes).parse(source)


def es5_single(text):
    return walker.extract(
        es5(text), lambda node: isinstance(node, asttypes.ExprStatement)
    ).expr


_WEBPACK_CONFIG_TEMPLATE = r"""'use strict';

var webpack = require('webpack');
var webpackConfig = {};
module.exports = webpackConfig;
"""


def identity(value):
    return value


def apply_webpack_mode(config):
    if 'mode' not in config:
        config['mode'] = DEFAULT_WEBPACK_MODE


def remove_webpack_mode(config):
    config.pop('mode', None)


config_rules = (
    (lt, ((4, 0),), remove_webpack_mode),
    (ge, ((4, 0),), apply_webpack_mode),
)


def clean_config(config, version_str, rules=config_rules):
    version = tuple(int(i) for i in version_str.split('.'))
    for operator, arguments, rule in rules:
        if operator(version, *arguments):
            rule(config)


class _WebpackConfigPlugins(MutableSequence):
    """
    A sequence specifically for webpack plugins.
    """

    def __init__(self, default=None):
        # note that the asttypes is one produced by the factory
        self.__node = asttypes.Array([])
        if default:
            self.extend(default)

    def __getitem__(self, key):
        return self.__node.items[key]

    def __setitem__(self, key, value):
        self.__node.items[key] = es5_single(value)

    def __delitem__(self, key):
        self.__node.items.__delitem__(key)

    def __iter__(self):
        return iter(self.__node.items)

    def __len__(self):
        return len(self.__node.items)

    def insert(self, index, value):
        self.__node.items.insert(index, es5_single(value))

    def __str__(self):
        return str(self.__node)

    def export(self):
        return asttypes.Array(list(self))


class WebpackConfig(MutableMapping):
    """
    An abstraction of a typical webpack configuration module.

    Provides a small set of helpers for setting up various webpack
    configuration options.  A method is also provided for serialization
    of the defined options to a webpack configuration script that is
    optimized to the specific supported webpack version(s).
    """

    # Ideally this implements the actual ECMAScript object data model,
    # but that is __way__ too much effort so this is still going to be
    # restricted to a standard Python dictionary.

    def __init__(self, *a, **kw):
        self.__special_mapping = {
            'plugins': _WebpackConfigPlugins
        }
        self.__config = {}
        self.__ast = es5(_WEBPACK_CONFIG_TEMPLATE)
        self.__ast_config = walker.extract(
            self.__ast, lambda node: isinstance(node, asttypes.Object))
        self.update(*a, **kw)

    def __getitem__(self, key):
        return self.__config[key]

    def __setitem__(self, key, value):
        # TODO spew out warnings for unsupported flags.
        self.__config[key] = self.__special_mapping.get(key, identity)(value)

    def __delitem__(self, key):
        self.__config.__delitem__(key)

    def __iter__(self):
        return iter(self.__config)

    def __len__(self):
        return len(self.__config)

    def __contains__(self, key):
        return key in self.__config

    def __str__(self):
        # map all special configurations options to config
        config = (
            (key, self.__config.get(key, NotImplemented))
            for key in self.__special_mapping
        )
        # make an assignment statement as bare objects are invalid code
        config_obj = es5_single('config = ' + dumps({
            k: v
            for k, v in self.__config.items()
            if k not in self.__special_mapping
        })).right
        # manually reassign them directly onto the config object AST
        for key, value in config:
            if value is NotImplemented:
                continue
            config_obj.properties.append(asttypes.Assign(
                left=asttypes.String('"%s"' % key), op=':',
                right=value.export(),
            ))
        self.__ast_config.properties = config_obj.properties
        return str(self.__ast)
