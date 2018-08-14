# -*- coding: utf-8 -*-
"""
Various utility functions
"""

import logging
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
from calmjs.webpack.manipulation import (
    inject_array_items_to_object_property_value,
)

logger = logging.getLogger(__name__)

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

_WEBPACK_4_DISABLE_JSON__MODULE_RULES_ = """
[{
    test: /\.(json|html)/,
    type: "javascript/auto",
    use: [],
}]
"""

# default list of webpack config plugins
_WEBPACK_CONFIG_PLUGINS = (
    # TODO figure out how to deal with chunking configuration
    'new webpack.optimize.LimitChunkCountPlugin({maxChunks: 1})',
)


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

    Note that this class should create a configuration file that is
    targeted towards the version of webpack declared by this package,
    and the optimized exports is a one-way conversion only.
    """

    # marker to denote the version of webpack to be targeted by this
    # class.
    __webpack_target__ = (4, 0, 0)

    # Ideally this implements the actual ECMAScript object data model,
    # but that is __way__ too much effort so this is still going to be
    # restricted to a standard Python dictionary.

    def __init__(self, *a, **kw):
        self.__special_mapping = {
            'plugins': _WebpackConfigPlugins,
            # define specific reserved keys (which will be filtered)
            '__webpack_target__': identity,
        }
        self.__config = {}
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

    def _generate_ast_and_config_node(
            self, template=_WEBPACK_CONFIG_TEMPLATE, skip=0):
        ast = es5(template)
        config_object_node = walker.extract(
            ast, lambda node: isinstance(node, asttypes.Object), skip=skip)
        return ast, config_object_node

    def _ast(self):
        """
        Subclass may override the generation of the AST.
        """

        ast, config_object_node = self._generate_ast_and_config_node()

        # map all special configurations options
        special_config = (
            (key, self.__config.get(key, NotImplemented))
            for key in self.__special_mapping
        )
        # make an assignment statement as bare objects are invalid code
        webpack_object = es5_single('config = ' + dumps({
            k: v
            for k, v in self.__config.items()
            if k not in self.__special_mapping
        })).right
        # manually reassign them directly onto the config object AST
        for key, value in special_config:
            if (value is NotImplemented or
                    self.__special_mapping.get(key) is identity):
                continue
            webpack_object.properties.append(asttypes.Assign(
                left=asttypes.String('"%s"' % key), op=':',
                right=value.export(),
            ))
        config_object_node.properties = finalize_webpack_object(
            webpack_object=webpack_object,
            version=self.get('__webpack_target__', self.__webpack_target__),
        ).properties
        return ast

    def __str__(self):
        return str(self._ast())


def finalize_webpack_object(webpack_object, version):
    exported_properties = []
    deferred = []
    for property_ in webpack_object.properties:
        finalized = _finalize_property(property_, version)
        if finalized is property_:
            exported_properties.append(finalized)
        elif callable(finalized):
            deferred.append(finalized)

    # reconstitute the webpack_object
    webpack_object.properties = exported_properties
    for finalize in deferred:
        finalize(webpack_object)

    return webpack_object


def identity_property(property_, version):
    return property_


def _webpack_mode(property_, version):
    value = property_.right
    if version < (4, 0, 0):
        if (isinstance(value, asttypes.String) and
                str(value)[1:-1] == DEFAULT_WEBPACK_MODE):
            logger.info(
                'unsupported property with default value removed for '
                'webpack %s: {%s}',
                '.'.join(str(v) for v in version), property_
            )
        else:
            logger.warning(
                'unsupported property with non-default value removed for '
                'webpack %s: {%s}; (un)expected (mis)behavior may occur',
                '.'.join(str(v) for v in version), property_
            )
        return
    return property_


def _disable_default_json_loader(property_, version):
    # this must be a webpack_config["module"]
    value = property_.right
    if version >= (4, 0, 0):
        rules = es5_single(_WEBPACK_4_DISABLE_JSON__MODULE_RULES_)
        logger.info(
            "disabling default json loader module rule for webpack %s",
            '.'.join(str(v) for v in version),
        )
        inject_array_items_to_object_property_value(
            value, asttypes.String('"rules"'), rules)

    return property_


def _webpack_optimization(property_, version):
    # this must be a webpack_config["optimization"]

    def apply_legacy_uglifyjs_plugin(config):
        inject_array_items_to_object_property_value(
            config, asttypes.String('"plugins"'), es5_single(
                '[new webpack.optimize.UglifyJsPlugin({})]'
            )
        )

    if version < (4, 0, 0):
        try:
            # this indiscriminately extract an assignment that has
            # "minimize": true
            walker.extract(property_.right, lambda node: (
                isinstance(node, asttypes.Assign) and
                isinstance(node.left, asttypes.String) and
                isinstance(node.right, asttypes.Boolean) and
                node.left.value == '"minimize"' and
                node.right.value == 'true'
            ))
        except TypeError:
            logger.info(
                'dropping unsupported property for webpack %s: {%s}',
                '.'.join(str(v) for v in version), property_
            )
        else:
            logger.info(
                'converting unsupported property to a plugin for '
                'webpack %s: {%s}',
                '.'.join(str(v) for v in version), property_
            )
            return apply_legacy_uglifyjs_plugin
        return
    return property_


def _finalize_property(property_, version, rules={
    '"mode"': _webpack_mode,
    '"module"': _disable_default_json_loader,
    '"optimization"': _webpack_optimization,
}):
    return rules.get(str(property_.left), identity_property)(
        property_, version)
