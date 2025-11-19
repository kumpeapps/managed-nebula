fastlane documentation
----

# Installation

Make sure you have the latest version of the Xcode command line tools installed:

```sh
xcode-select --install
```

For _fastlane_ installation instructions, see [Installing _fastlane_](https://docs.fastlane.tools/#installing-fastlane)

# Available Actions

## Mac

### mac certs

```sh
[bundle exec] fastlane mac certs
```

Import Developer ID certificates for macOS distribution

### mac list_identities

```sh
[bundle exec] fastlane mac list_identities
```

List available code signing identities

### mac build_production

```sh
[bundle exec] fastlane mac build_production
```

Build production-signed installer with code signing and notarization

----


## iOS

### ios update_match

```sh
[bundle exec] fastlane ios update_match
```

Updates match certificates

### ios matchget

```sh
[bundle exec] fastlane ios matchget
```



----

This README.md is auto-generated and will be re-generated every time [_fastlane_](https://fastlane.tools) is run.

More information about _fastlane_ can be found on [fastlane.tools](https://fastlane.tools).

The documentation of _fastlane_ can be found on [docs.fastlane.tools](https://docs.fastlane.tools).
