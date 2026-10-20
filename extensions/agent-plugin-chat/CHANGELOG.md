# Changelog

All notable changes to the Python Shiny: Chat with Connect-managed skills extension will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.0.1] - 2026-09-22

### Added

- Initial release. A Shiny chat app whose skills come from the Connect agent
  plugin marketplaces its viewer is entitled to, so one deployment serves
  everyone and each person's agent gets only what an administrator granted
  them.
- Skills reach the model three ways: a `load_skill` tool the model calls when
  it judges a skill relevant, a `/<skill-name>` slash command the person
  invokes directly, and sidebar pinning that applies a skill to the whole
  conversation.
- Colliding skill names are disambiguated rather than resolved by clone order,
  falling back to `plugin:skill` and then `plugin:skill@marketplace`.
