# -*- coding: utf-8 -*-
"""
Various utility functions
"""

from __future__ import unicode_literals

import logging
from collections import MutableMapping
from collections import MutableSequence
from json import dumps

# these are the specific instances used for type checking
from calmjs.parse.asttypes import (
    Assign,
    Boolean,
    ExprStatement,
    Node,
    Object,
    String,
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
        es5(text), lambda node: isinstance(node, ExprStatement)
    ).expr


_WEBPACK_CONFIG_TEMPLATE = """'use strict';

var webpack = require('webpack');
var webpackConfig = {};
module.exports = webpackConfig;
"""

_WEBPACK_KARMA_CONFIG_TEMPLATE = """'use strict';
var webpack = require('webpack');

// this defines the kill plugin that will be added later.
var KillPlugin = function() {};
KillPlugin.prototype.apply = function(compiler) {
    compiler.plugin('done', function(stats) {
        if (stats.hasErrors()) {
            setTimeout(function() {
                process.exit(2);
            }, 0);
        }
    });
};

module.exports = function(config) {
    var karma_conf_json = {};
    // karma_conf_json.webpack = {};
    config.set(karma_conf_json);
}
"""

_WEBPACK_4_DISABLE_JSON__MODULE_RULES_ = """
[{
    test: /\.(json|html)/,
    type: "javascript/auto",
    use: [],
}]
"""

# default list of webpack config plugins
# TODO figure out how to best customize chunking configuration
_WEBPACK_CONFIG_PLUGINS = """[
    new webpack.optimize.LimitChunkCountPlugin({maxChunks: 1}),
]"""

# default list of additional karma plugins
_WEBPACK_KARMA_CONFIG_PLUGINS = """[
    new KillPlugin(),
]"""


def identity(value):
    return value


# Ideally, for the implementaiton following mapping types, they be done
# closer to the actual ECMAScript object data model (say the asttypes),
# but that is __way__ too much effort so this is still going to be
# restricted to a standard Python dictionary.

class ConfigMapping(MutableMapping):
    """
    A mapping class that has a built-in concept of reserved special keys
    that should be mapped to some specific data type, done in a manner
    that is standard to this module.
    """

    def __init__(self, *a, **kw):
        self._config = {}
        self._setup()
        self.update(*a, **kw)

    def _setup(self):
        # subclasses should override this to provide specific
        # _special_mapping
        self._special_mapping = {}

    def __getitem__(self, key):
        return self._config[key]

    def __setitem__(self, key, value):
        self._config[key] = self._special_mapping.get(key, identity)(value)

    def __delitem__(self, key):
        self._config.__delitem__(key)

    def __iter__(self):
        return iter(self._config)

    def __len__(self):
        return len(self._config)

    def __contains__(self, key):
        return key in self._config

    def json(self):
        """
        Return a JSON encoded version of the mapping without any of the
        keys specified in the _special_mapping.
        """

        return dumps({
            k: v
            for k, v in self._config.items()
            if k not in self._special_mapping
        })

    def es5(self):
        """
        Produce a representation of the configuration, inclusive of the
        keys in the special mapping, as a ES5 object node.
        """

        # map all special configurations options
        special_config = (
            (key, self._config.get(key, NotImplemented))
            for key in self._special_mapping
        )
        # make an assignment statement as bare objects are invalid code
        json_node = es5_single('config = ' + self.json()).right
        # manually reassign them directly onto the config object AST
        for key, value in special_config:
            if (value is NotImplemented or
                    self._special_mapping.get(key) is identity):
                continue
            json_node.properties.append(asttypes.Assign(
                left=asttypes.String('"%s"' % key), op=':',
                right=value.es5(),
            ))
        return json_node


class ConfigCodeSequence(MutableSequence):
    """
    A sequence specifically for ES5 code.
    """

    def __init__(self, default=None):
        # note that the asttypes is one produced by the factory
        self.__node = asttypes.Array([])
        if default:
            self.extend(default)

    def __getitem__(self, key):
        return self.__node.items[key]

    def __setitem__(self, key, value):
        self.__node.items[key] = self._value(value)

    def __delitem__(self, key):
        self.__node.items.__delitem__(key)

    def __iter__(self):
        return iter(self.__node.items)

    def __len__(self):
        return len(self.__node.items)

    def _value(self, value):
        return value if isinstance(value, Node) else es5_single(value)

    def insert(self, index, value):
        self.__node.items.insert(index, self._value(value))

    def __str__(self):
        return str(self.__node)

    def json(self):
        # since it's all ES5 code, none of the elements should produce
        # JSON.
        return '[]'

    def es5(self):
        return asttypes.Array(list(self))


class _WebpackConfigPlugins(ConfigCodeSequence):
    """
    A sequence specifically for webpack plugins.
    """


class WebpackConfig(ConfigMapping):
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

    def _setup(self):
        self._special_mapping = {
            'plugins': _WebpackConfigPlugins,
            # define specific reserved keys (which will be filtered)
            '__webpack_target__': identity,
        }

    # TODO spew out warnings for unsupported flags.
    # def __setitem__(self, key, value):
    #     # if key not in webpack_grammar:
    #     #     logger.warning('key %s not in webpack grammar', key)
    #     super(WebpackConfig, self).__setitem__(self, key, value)

    def es5(self):
        return finalize_webpack_object(
            webpack_object=super(WebpackConfig, self).es5(),
            version=self.get('__webpack_target__', self.__webpack_target__),
        )

    def __str__(self):
        ast, config_object_node = generate_ast_and_config_node(
            _WEBPACK_CONFIG_TEMPLATE)
        config_object_node.properties = self.es5().properties
        return str(ast)


class KarmaWebpackConfig(ConfigMapping):
    """
    An abstraction of a karma.conf.js file with a webpack property.

    Like the WebpackConfig mapping, it is set up to track the required
    special mapping (which is WebpackConfig in this case).
    """

    def _setup(self):
        self._special_mapping = {
            'webpack': WebpackConfig,
        }
        # preassign specific reserved values
        self['webpack'] = {}

    def __str__(self):
        ast, config_object_node = generate_ast_and_config_node(
            _WEBPACK_KARMA_CONFIG_TEMPLATE)
        karma_node = self.es5()

        try:
            webpack_object_node = walker.extract(karma_node, lambda node: (
                isinstance(node, Assign) and
                isinstance(node.right, Object) and
                isinstance(node.left, String) and
                node.left.value == '"webpack"'
            )).right
        except TypeError:
            raise KeyError(
                "'webpack' attribute missing in karma configuration object")

        inject_array_items_to_object_property_value(
            webpack_object_node, asttypes.String('"plugins"'),
            es5_single(_WEBPACK_KARMA_CONFIG_PLUGINS),
        )

        config_object_node.properties = karma_node.properties
        return str(ast)


def generate_ast_and_config_node(template, skip=0):
    ast = es5(template)
    config_object_node = walker.extract(
        ast, lambda node: isinstance(node, Object), skip=skip)
    return ast, config_object_node


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

    inject_array_items_to_object_property_value(
        webpack_object, asttypes.String('"plugins"'),
        es5_single(_WEBPACK_CONFIG_PLUGINS),
    )

    return webpack_object


def identity_property(property_, version):
    return property_


def _webpack_mode(property_, version):
    value = property_.right
    if version < (4, 0, 0):
        if (isinstance(value, String) and
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
                isinstance(node, Assign) and
                isinstance(node.left, String) and
                isinstance(node.right, Boolean) and
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
