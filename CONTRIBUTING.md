# NLDI Contribution Guidelines

First, Thank you for considering a contribution. This project is
a community resource, its success is contingent on your contributions.

## Linked Data Contribution

Linked data contributions are made through a configuration of the
[NLDI Crawler](https://github.com/internetofwater/nldi-crawler#contributing) in the
[NLDI Database](https://github.com/internetofwater/nldi-db/blob/master/liquibase/changeLogs/nldi/nldi_data/update_crawler_source/crawler_source.tsv).

For support in this process, open
[an issue in the NLDI-Services](https://github.com/internetofwater/nldi-services/issues) repository.

## Code Contribution

Contribution to the overall project are more than welcome. Please open
an issue describing the goal of your contribution in the
[NLDI-Services](https://github.com/internetofwater/nldi-services/issues)
repository prior to opening a pull request.

Contributions may ultimately reside in the services, database, or crawler
repositories. All pull requests should link back to the issues in the
services repository to ensure we track contributions in a single location.

## Ideas and Bug Reports

For ideas for new features and bug reports, please register them as
issues in the [NLDI-Services](https://github.com/internetofwater/nldi-services/issues)
repository.

## Build workflow for NLDI-py Container

Tests are intended to run on your workstation; there is not a mechanism (yet) to run these
tests in a CI/CD pipeline.

We use a feature-branch model for changes.  Each added feature or bugfix should be applied
as a branch/fork and merged into `main` using the standard PR process.  The last commit
of the feature branch should be an update to the version number in the `pyproject.toml`.
This is most easily done with `uv version` command (i.e. `uv version --bump patch`), but
could also be edited manually.

The commit message on a PR merge to main will be used in the release notes for future releases.

Create a release with an appropriate tag using semantic versioning.  GitHub will
auto-generate release notes since the last release.  Edit as needed.

Upon creation of the release, a GitHub Action will build a docker image and tag it
with the same tag you used to make this release.  That image will then be available
via `ghcr.io`.
