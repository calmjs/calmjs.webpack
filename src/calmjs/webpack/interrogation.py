# -*- coding: utf-8 -*-
"""
A collection of functions for interrogating a webpack artifact so that
useful information may be extracted.
"""

from calmjs.parse.asttypes import Assign
from calmjs.parse.asttypes import Array
from calmjs.parse.asttypes import BracketAccessor
from calmjs.parse.asttypes import Comma
from calmjs.parse.asttypes import DotAccessor
from calmjs.parse.asttypes import FuncExpr
from calmjs.parse.asttypes import FunctionCall
from calmjs.parse.asttypes import Number
from calmjs.parse.asttypes import Object
from calmjs.parse.asttypes import Return
from calmjs.parse.asttypes import String

from calmjs.parse.visitors.generic import ConditionalVisitor

visitor = ConditionalVisitor()
extract = visitor.extract


def probe(node):
    # first, find the initial function expression
    webpack_wrapper = extract(node, lambda n: isinstance(n, FuncExpr))
    # this is the factory argument
    factory_name = webpack_wrapper.parameters[1].value

    if factory_name == 'factory':
        verify_factory(webpack_wrapper, factory_name)
        index = extract_position(node)
    else:
        # assuming it's a minified source
        verify_factory_min(webpack_wrapper, factory_name)
        index = extract_position_min(node)

    module = extract_module(node, index)
    names = extract_exported_calmjs_names(module)
    return names


def verify_factory(node, factory_name):
    return extract(node, lambda n: (
        isinstance(n, Assign) and
        isinstance(n.left, BracketAccessor) and
        n.left.expr.value == '"__calmjs__"' and
        n.right.identifier.value == factory_name
    ))


def extract_position(node):
    return int(extract(node, lambda n: (
        isinstance(n, Return) and
        isinstance(n.expr, FunctionCall) and
        n.expr.args.items and
        isinstance(n.expr.args.items[0], Assign) and
        isinstance(n.expr.args.items[0].right, Number) and
        n.expr.identifier.value == '__webpack_require__'
    )).expr.args.items[0].right.value)


def verify_factory_min(node, factory_name):
    return extract(node, lambda n: (
        isinstance(n, Assign) and
        isinstance(n.left, DotAccessor) and
        n.left.identifier.value == '__calmjs__' and
        n.right.identifier.value == factory_name
    ))


def extract_position_min(node):
    return int(extract(node, lambda n: (
        isinstance(n, Return) and
        isinstance(n.expr, Comma) and
        isinstance(n.expr.right, FunctionCall) and
        n.expr.right.args.items and
        isinstance(n.expr.right.args.items[0].right, Number)
    )).expr.right.args.items[0].right.value)


def extract_module(node, index):
    return extract(node, lambda n: (
        isinstance(n, Return) and
        isinstance(n.expr, FunctionCall) and
        n.expr.args.items and
        isinstance(n.expr.args.items[0], Array)
    )).expr.args.items[0].items[index]


def extract_exported_calmjs_names(module_node):
    return [to_identifier(p.left) for p in extract(
        module_node, lambda n: (
            isinstance(n, Assign) and
            isinstance(n.left, DotAccessor) and
            isinstance(n.right, Object) and
            n.left.identifier.value == 'modules'
        )
    ).right.properties]


def to_identifier(node):
    # if the node is a string, assume it is used as a BracketAccessor
    if isinstance(node, String):
        # We are leveraging the similarity of string encoding between
        # ES5 and Python, but to achieve this is a bit of work.
        # First, the quotes must be stripped ([1:-1]), then use the
        # unicode-escape to encode all the things - and then strip off
        # the doubly escaped backslashes for everything and bring it
        # back by decoding again with unicode-escape.
        return node.value[1:-1].encode('unicode-escape').replace(
            b'\\\\', b'\\').decode('unicode-escape')
    else:
        # assume to be an Identifier
        return node.value
