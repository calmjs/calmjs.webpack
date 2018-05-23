# -*- coding: utf-8 -*-
"""
CalmJS webpack artifact generation helpers
"""

from calmjs.toolchain import Spec
from calmjs.toolchain import SETUP
from calmjs.webpack.cli import create_spec
from calmjs.webpack.cli import default_toolchain

from calmjs.webpack.dev import webpack_advice


def complete_webpack(package_names, export_target):
    """
    Return the toolchain and a spec that when executed together, will
    result in a complete artifact using the provided package names onto
    the export_target.
    """

    return default_toolchain, create_spec(package_names, export_target)


def test_complete_webpack(package_names, export_target):
    """
    Accompanied testing entry point for the complete_webpack artifact.
    """

    # importing in here as calmjs.dev is an optional dependency.
    from calmjs.dev.toolchain import KarmaToolchain

    spec = Spec(
        export_target=export_target,
        test_package_names=package_names,
    )
    spec.advise(SETUP, webpack_advice, spec)
    return KarmaToolchain(), spec


def optimize_webpack(package_names, export_target):
    """
    Return the toolchain and a spec that when executed together, will
    result in a complete artifact using the provided package names onto
    the export_target, with the optimize options enabled.
    """

    return default_toolchain, create_spec(
        package_names, export_target,
        webpack_optimize_minimize=True,
    )
