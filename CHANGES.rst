Changelog
=========

0.0.0 (unreleased)
------------------

- Initial implementation of the Calmjs integration tool that enable the
  production of webpack artifacts from JavaScript sources that are
  included with Python packages, that also allow import of their
  dependencies sourced through ``npm`` through the Calmjs framework.
- Enabled the ``calmjs webpack`` tool entry point.
- Also provide integration with ``calmjs.dev`` by correcting the correct
  hooks so that this package can be used as an advice package for the
  execution of tests against artifacts generated through this package,
  through the usage of ``calmjs karma webpack``.
