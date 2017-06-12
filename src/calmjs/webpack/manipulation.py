# -*- coding: utf-8 -*-
"""
A collection of helpers for manipulating ES5 sources.
"""

from calmjs.parse.asttypes import Array
from calmjs.parse.asttypes import DotAccessor
from calmjs.parse.asttypes import FunctionCall
from calmjs.parse.asttypes import Identifier
from calmjs.parse.asttypes import String

from calmjs.webpack.interrogation import visitor
from calmjs.webpack.visitor import ReplacementVisitor

replacer = ReplacementVisitor()


def _non_asttypes_string(arg):
    if isinstance(arg, String):
        return False

    # first check whether AMD syntax is used
    if isinstance(arg, Array):
        return any(filter(lambda n: not isinstance(n, String), arg))
    # otherwise this is assumed to be dynamic.
    return True


def extract_dynamic_require(node):
    """
    Return require() function calls that have one or more non-static
    arguments (i.e. first argument not String).
    """

    return visitor.generate(node, lambda n: (
        isinstance(n, FunctionCall) and
        isinstance(n.identifier, Identifier) and
        n.identifier.value == 'require' and
        n.args and _non_asttypes_string(n.args[0])
    ))


def create_calmjs_require(node):
    """
    Replace the dynamic requires in the node with the calmjs version.
    """

    # node is a FunctionCall
    # TODO the source map related attributes may need to be copied over
    # from the existing FunctionCall  node.
    return FunctionCall(
        args=node.args,
        identifier=DotAccessor(
            node=FunctionCall(
                args=[String("'__calmjs__'")],
                identifier=Identifier(value='require'),
            ),
            # preserve the original identifier within the DotAccessor itself
            identifier=node.identifier,
        )
    )


def convert_dynamic_require(tree):
    """
    Take the given tree, generate a conversion table and apply the
    transformation in-place in the tree.  Also return the tree.
    """

    nodemap = {
        node: create_calmjs_require(node)
        for node in extract_dynamic_require(tree)
    }
    replacer.replace(tree, nodemap)
    return tree
