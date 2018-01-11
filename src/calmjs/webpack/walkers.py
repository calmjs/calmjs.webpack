# -*- coding: utf-8 -*-
"""
Various walkers.
"""

from calmjs.parse.asttypes import Node


def _replace_list_item(list_, idx, replacement):
    if replacement:
        list_[idx] = replacement


def _replace_list_items(tree, attr, itemmap):
    list_ = getattr(tree, attr)
    for idx, item in enumerate(list_):
        _replace_list_item(list_, idx, itemmap.get(item))


def _replace_obj_attr(tree, attr, itemmap):
    replacement = itemmap.get(getattr(tree, attr), NotImplemented)
    if replacement is not NotImplemented:
        setattr(tree, attr, replacement)


class ReplacementWalker(object):

    def __init__(self):
        self.methods = [
            (list, _replace_list_items),
            (Node, _replace_obj_attr),
        ]

    def replace(self, tree, nodemap):
        """
        With a given tree, walk and replace all nodes represented in the
        node map.

        The replace method processes the tree in two passes per child.
        First pass will recursively check through all children through
        the standard Node.children method call.  Second pass will then
        look for the actual attributes of the Node and the replacement
        will then occur with entities as specified by the nodemap.
        """

        # first, go through the standard API for the nested call, i.e.
        # depth first.
        for child in tree.children():
            if child is None:
                # a missing value might be an upstream bug?
                continue
            self.replace(child, nodemap)

        # second, go through the individual vars within the object and
        # verify.
        for attr, value in vars(tree).items():
            for t, m in self.methods:
                if isinstance(value, t):
                    m(tree, attr, nodemap)
                    continue
