Example data
============

These pre-built packages are manually generated from the test cases
found in the ``test_integration`` test module, specifically using the
following test case methods:

- ``ToolchainIntegrationTestCase.test_webpack_toolchain_standard_only``
- ``ToolchainIntegrationTestCase.test_webpack_toolchain_with_bundled``

A manual breakpoint was inserted so that another break can be added
shortly before the actual compile step was done, so that the manually
executed ``webpack --config ${webpack_config}`` was done, with the
minified one executed with the ``--optimize-minimize`` flag enabled.
