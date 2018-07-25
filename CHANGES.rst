Changelog
=========

1.1.0 (2018-07-25)
------------------

- Provide support of prefix-free loaders through a customized webpack
  loader module registry; this one also works in tandem with the
  ``calmjs.module`` registry.  [
  `#5 <https://github.com/calmjs/calmjs.webpack/issues/5>`_
  ]

  - Integrate the support of the package resource loader registry
    introduced by ``calmjs-3.3.0``.
  - Bumped supported ``calmjs.dev`` to version 2.2.0 such that the
    correct test loader registries can be automatically acquired.  This
    also makes it possible to declare test data files as resources for
    JavaScript tests in the most straightforward manner as possible

- The base loader plugin handler will also generate a modname prefixed
  with ``./``, in an attempt to provide a more natural include mechanism
  from within certain webpack loader contexts, as a number of them will
  implicitly resolve by relative path for a bare import, and the goal is
  to avoid further proprietary webpack syntaxes (e.g. the usage of the
  ``~`` prefixes to some ``namespace/package`` import/inclusions done
  inside the loader context).  [
  `#4 <https://github.com/calmjs/calmjs.webpack/issues/4>`_
  ]

1.0.2 (2018-05-24)
------------------

- Provide a builder that will generate an artifact with the supported
  optimize flags enabled. [
  `#3 <https://github.com/calmjs/calmjs.webpack/issues/3>`_
  ]

1.0.1 (2018-05-03)
------------------

- Update the export_target production and usage of working_dir to be
  inline with what is expected by ``calmjs-3.1.0``. [
  `#2 <https://github.com/calmjs/calmjs.webpack/issues/2>`_
  ]

1.0.0 (2018-01-12)
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
- Support for prebuilt artifacts for packages is provided through
  ``calmjs.artifacts`` registry; default complete builders for both
  building and testing are available via the ``calmjs.webpack.artifact``
  module.
- Webpack is pinned to ~2.6.0, as that is the current stable version
  that is verified to work with building and testing of artifacts.
