# CHANGELOG


## v0.10.1 (2026-11-02)

### Bug Fixes

- Accept device names and firmware versions seen on paired devices
  ([#22](https://github.com/AustinBrunkhorst/pysnooz/pull/22),
  [`c006e5f`](https://github.com/AustinBrunkhorst/pysnooz/commit/c006e5f328f7170aded8d7420c36832d8b6a34b2))

Paired devices aren't always seen under a "Snooz-XXXX" name: some stacks report the device name
  characteristic ("Snooz") after connecting, and a Pro model has been observed as "Szpro EF22". The
  strict advertisement parser introduced in 0.9.0 rejected those, which breaks setup of existing
  devices once a client parses the cached advertisement (home-assistant/core#183827).

- accept any name starting with Snooz, Szpro or Breez - never mark a known firmware version as
  unsupported - only require the state characteristics to connect; the command and device info
  characteristics are optional

Also bumps the bandit pre-commit hook to 1.9.4. The 1.7.5 hook environment no longer installs pbr,
  which had been failing the lint job and blocking the release job on main since May.

- Race condition in disconnect routine ([#19](https://github.com/AustinBrunkhorst/pysnooz/pull/19),
  [`aed332f`](https://github.com/AustinBrunkhorst/pysnooz/commit/aed332f23236feafd2adcbbc1c8cbf8f9fa37aa4))

### Chores

- Bleak 1.0.0 API changes ([#20](https://github.com/AustinBrunkhorst/pysnooz/pull/20),
  [`489caeb`](https://github.com/AustinBrunkhorst/pysnooz/commit/489caeb1123ddf2f4b571862e76c22bc07f69f6e))

* fix: make compatible with bleak 1.0.0 API changes

* chore: relock with bleak>=1.0.0

### Continuous Integration

- Bump python-semantic-release action to v9.21.2
  ([#23](https://github.com/AustinBrunkhorst/pysnooz/pull/23),
  [`9f5e9d5`](https://github.com/AustinBrunkhorst/pysnooz/commit/9f5e9d57aab99d640e43082bcbb402818e82d23d))

The v8.0.0 action builds its image from Debian bullseye, whose security repository no longer serves
  git-lfs, so the release job failed before semantic-release ran. v9.21.2 builds on bookworm and
  reads the existing configuration unchanged.


## v0.10.0 (2023-09-13)

### Features

- Button light controls ([#17](https://github.com/AustinBrunkhorst/pysnooz/pull/17),
  [`ee76bed`](https://github.com/AustinBrunkhorst/pysnooz/commit/ee76bedc64c9b466bc34cdfd30eb787218bc6a6a))

* feat: light controls

* test: lights and night mode

* feat: night mode brightness configurable

* fix: light on state

* revert: command repr

* docs: add light commands to readme


## v0.9.2 (2023-09-11)

### Bug Fixes

- Update README to list all commands
  ([`c0f3b2d`](https://github.com/AustinBrunkhorst/pysnooz/commit/c0f3b2da79c3ee76309ab83cb2288de83c64db63))

### Testing

- Cancelled command execution raises ([#16](https://github.com/AustinBrunkhorst/pysnooz/pull/16),
  [`da9177b`](https://github.com/AustinBrunkhorst/pysnooz/commit/da9177bc28c027039c3ad60c92a7294ddf1db99d))


## v0.9.1 (2023-09-10)

### Bug Fixes

- Commands execution can be cancelled without disconnect
  ([#15](https://github.com/AustinBrunkhorst/pysnooz/pull/15),
  [`f4b4111`](https://github.com/AustinBrunkhorst/pysnooz/commit/f4b41118705358a7b7cbf8a64e9b84f8a2b5315c))


## v0.9.0 (2023-09-10)

### Features

- Support for breez and pro devices ([#14](https://github.com/AustinBrunkhorst/pysnooz/pull/14),
  [`3b823c8`](https://github.com/AustinBrunkhorst/pysnooz/commit/3b823c8272864352220838ccbddb97655afb311c))

* test: improve coverage

* test: update pyproject.toml for tests

* test: add device properties for testing

* test: add coverage for mock clients

* test: mock client handles disconnect properly

* test: states are copied in mock clients

* docs: add supported devices, update usage

---------

Co-authored-by: github-actions <github-actions@github.com>


## v0.8.6 (2023-08-30)

### Bug Fixes

- Unsubscribe from events after disconnect
  ([`14ef0b4`](https://github.com/AustinBrunkhorst/pysnooz/commit/14ef0b48a1b7da04517246c7b3612814e7a98572))

### Chores

- Ci uses python 3.11
  ([`94fcf4c`](https://github.com/AustinBrunkhorst/pysnooz/commit/94fcf4cf1f2803cc4bf0341ab39772261cf1b400))

- Update other python references
  ([`a59a48f`](https://github.com/AustinBrunkhorst/pysnooz/commit/a59a48fd4b62f5cab22018d23a0f0791f128db92))

- Update to python 3.11
  ([`c0cc57f`](https://github.com/AustinBrunkhorst/pysnooz/commit/c0cc57f22b14f2ebbe7b00e3952f4e9b57af4d1a))

### Continuous Integration

- Add contents write permission
  ([`c8e1a46`](https://github.com/AustinBrunkhorst/pysnooz/commit/c8e1a46d4b72b4b50cf1a7b0f4bed9d8c82b73a2))

- Fix semantic release toml definitions
  ([`1dba5db`](https://github.com/AustinBrunkhorst/pysnooz/commit/1dba5dbdd88b9b64dfcd0ef6ffd0b0467a4b4348))

- Revert to python 3.10
  ([`270dd16`](https://github.com/AustinBrunkhorst/pysnooz/commit/270dd168257df3edfdf9a6123abf3dd86155f2cf))

- Update semantic release
  ([`6fd209e`](https://github.com/AustinBrunkhorst/pysnooz/commit/6fd209ec54279b51c18b8b507ad63db7af5c2076))

### Documentation

- Add epenet as a contributor for code ([#13](https://github.com/AustinBrunkhorst/pysnooz/pull/13),
  [`8a4e372`](https://github.com/AustinBrunkhorst/pysnooz/commit/8a4e37232c258ecbc10773e295b0e3019c73e4f7))

* docs: update README.md [skip ci]

* docs: update .all-contributorsrc [skip ci]

---------

Co-authored-by: allcontributors[bot] <46447321+allcontributors[bot]@users.noreply.github.com>


## v0.8.5 (2023-05-24)

### Bug Fixes

- Race condition during disconnect ([#7](https://github.com/AustinBrunkhorst/pysnooz/pull/7),
  [`d1ac03f`](https://github.com/AustinBrunkhorst/pysnooz/commit/d1ac03fa16a5d17a9b9a7252d6e6baaadc5a7768))

### Chores

- Update build status badge
  ([`4efb497`](https://github.com/AustinBrunkhorst/pysnooz/commit/4efb497a2af8fda7540ddd94d853f885293f12d3))

[skipci]

### Documentation

- Add mweinelt as a contributor for code
  ([#12](https://github.com/AustinBrunkhorst/pysnooz/pull/12),
  [`5b291df`](https://github.com/AustinBrunkhorst/pysnooz/commit/5b291df26551d5da7137351ab0d3ddae4cf71be8))

* docs: update README.md [skip ci]

* docs: update .all-contributorsrc [skip ci]

---------

Co-authored-by: allcontributors[bot] <46447321+allcontributors[bot]@users.noreply.github.com>


## v0.8.4 (2023-05-23)

### Bug Fixes

- Repair test compatibility with bleak>=0.20.0
  ([#9](https://github.com/AustinBrunkhorst/pysnooz/pull/9),
  [`f789d92`](https://github.com/AustinBrunkhorst/pysnooz/commit/f789d9253640a43ca7c8f2f9b8530d017667178c))

With the bleak 0.20.0 release the rssi and metadata attributes on the BLEDevice object became
  properties, that need to be initialized in the constructor. This broke parts of the test suite,
  that this changeset fixes.

Closes: #8

### Chores

- Update dependencies, target python 3.10
  ([#10](https://github.com/AustinBrunkhorst/pysnooz/pull/10),
  [`ac2ea3f`](https://github.com/AustinBrunkhorst/pysnooz/commit/ac2ea3f36252bb5540a4e44dfb42aa49476dea59))

* chore: update dependencies, target python 3.10

* chore: run black formatter


## v0.8.3 (2022-10-27)

### Bug Fixes

- Use BleakClientWithServiceCache
  ([`fdd9b32`](https://github.com/AustinBrunkhorst/pysnooz/commit/fdd9b32836ff5320e0bda1f1c7bf60c667bf3145))

- Use BleakClientWithServiceCache
  ([`e828fe8`](https://github.com/AustinBrunkhorst/pysnooz/commit/e828fe8f72df898ea6c8d1a45180568f0333b14b))

### Continuous Integration

- Temporarily disable broken windows tests
  ([`bf8a259`](https://github.com/AustinBrunkhorst/pysnooz/commit/bf8a2596347360f45a6bf2648556c373caa1b968))

- Update action dependency
  ([`7893894`](https://github.com/AustinBrunkhorst/pysnooz/commit/7893894f0189097eda81f9fdf18f7cf420189780))


## v0.8.2 (2022-10-10)

### Bug Fixes

- Update write_gatt_char for CoreBluetooth backend
  ([`c1bafc3`](https://github.com/AustinBrunkhorst/pysnooz/commit/c1bafc3c35a1cc445f2078c4d3a00451243e5f25))

### Continuous Integration

- Update pre-commit/action to v3.0.0
  ([`9fff0a9`](https://github.com/AustinBrunkhorst/pysnooz/commit/9fff0a96d42e98510a1001acbdadc9581b2bcf0f))


## v0.8.1 (2022-10-08)

### Bug Fixes

- Corebluetooth backend notifications
  ([`d476816`](https://github.com/AustinBrunkhorst/pysnooz/commit/d4768164e739393a580296e298f2da8a20b4392b))


## v0.8.0 (2022-10-08)

### Bug Fixes

- Add mock device
  ([`7c62a1b`](https://github.com/AustinBrunkhorst/pysnooz/commit/7c62a1b092b66b182bed0414dd4c7f5a354aaec2))


## v0.7.9 (2022-10-08)

### Bug Fixes

- Refactor deprecated bleak disconnect callback
  ([`2491051`](https://github.com/AustinBrunkhorst/pysnooz/commit/2491051bb197df6ba18218cb2ebfa39bacfd89da))

### Features

- Make loop optional on device
  ([`09ea58d`](https://github.com/AustinBrunkhorst/pysnooz/commit/09ea58d8b6bfc1e52a86880dc8bfd02ef3828d71))


## v0.7.8 (2022-10-01)


## v0.7.7 (2022-09-18)

### Bug Fixes

- Bump bleak and bleak-retry-connector
  ([`1c79ae4`](https://github.com/AustinBrunkhorst/pysnooz/commit/1c79ae41ea4a0cc5f6afd6b6aedfa824446c097b))

- Include mock client in main package
  ([`27dfbd6`](https://github.com/AustinBrunkhorst/pysnooz/commit/27dfbd6d71d9b2874f417dbd94cb24824ae932e2))


## v0.7.6 (2022-09-14)

### Testing

- Include mock client to main package
  ([`ce898fa`](https://github.com/AustinBrunkhorst/pysnooz/commit/ce898fabcd5584211b9866ad567cdb770d970c44))


## v0.7.5 (2022-09-14)

### Bug Fixes

- Bump bleak to 0.17.0
  ([`db3a57a`](https://github.com/AustinBrunkhorst/pysnooz/commit/db3a57a706a49cc21294226098ca1cafd4d19689))

- Loosen package constraints
  ([`34f0a14`](https://github.com/AustinBrunkhorst/pysnooz/commit/34f0a145e74ad9c2c7c7a14308061079f93f324f))


## v0.7.4 (2022-09-08)

### Bug Fixes

- Bump bleak to 0.17.0
  ([`010b311`](https://github.com/AustinBrunkhorst/pysnooz/commit/010b31172c936626db8d4c3dc0269d01057c10ab))

- Bump bluetooth packages
  ([`595e575`](https://github.com/AustinBrunkhorst/pysnooz/commit/595e57564857cbbb0000c19dc7746b0ae9264677))


## v0.7.3 (2022-08-31)

### Documentation

- Update .all-contributorsrc [skip ci]
  ([`b943305`](https://github.com/AustinBrunkhorst/pysnooz/commit/b94330500816d7423d11cde4ade6e4de64acc2cf))

- Update README
  ([`828ce0d`](https://github.com/AustinBrunkhorst/pysnooz/commit/828ce0d02d6e3fe5c0959a02855585a73b997246))

- Update README.md [skip ci]
  ([`f11d8fd`](https://github.com/AustinBrunkhorst/pysnooz/commit/f11d8fdb65f4e6e17f67c2aa717a5e5bf0607306))


## v0.7.2 (2022-08-31)

### Bug Fixes

- Improve resilience for exceptions
  ([`349ad59`](https://github.com/AustinBrunkhorst/pysnooz/commit/349ad59dacbfa7220bc5fe05197262e67c0959e6))

- Issue URL + sleep on write retry
  ([`bc57d51`](https://github.com/AustinBrunkhorst/pysnooz/commit/bc57d510a3288ca234390583d71d2e1f02c55bc6))


## v0.7.1 (2022-08-30)

### Chores

- Update readme
  ([`fe687ef`](https://github.com/AustinBrunkhorst/pysnooz/commit/fe687ef645d14c88c76136eb9160cb43d01b0547))


## v0.7.0 (2022-08-30)

### Bug Fixes

- Add missing f-string
  ([`8637d3b`](https://github.com/AustinBrunkhorst/pysnooz/commit/8637d3b00d4307461d5229e4b822895daa4896de))

### Features

- **docs**: Add initial usage
  ([`1d3f439`](https://github.com/AustinBrunkhorst/pysnooz/commit/1d3f43937493573c6979d01f91b01f7998d55edd))


## v0.6.2 (2022-08-30)

### Testing

- **advertisement**: Add advertisement tests
  ([`9dd5b81`](https://github.com/AustinBrunkhorst/pysnooz/commit/9dd5b815ab9db54fdca2a104e1a15a9dc4bb3bc3))

- **api**: Fix mock warnings
  ([`3b03e74`](https://github.com/AustinBrunkhorst/pysnooz/commit/3b03e74ea57a74fb919ef6540ac8b5dcd8039fe9))

- **api**: Use magic mock instead of async mock
  ([`ae5194e`](https://github.com/AustinBrunkhorst/pysnooz/commit/ae5194ea14b07041bdf24e79f547d1aa0a23afec))


## v0.6.1 (2022-08-30)

### Bug Fixes

- **logs**: Add logs + api tests
  ([`c587f81`](https://github.com/AustinBrunkhorst/pysnooz/commit/c587f81357f1a70ce46af118c77b65cb1b9ab568))


## v0.6.0 (2022-08-30)

### Bug Fixes

- **log**: Use formatted message for status change
  ([`4dc4a20`](https://github.com/AustinBrunkhorst/pysnooz/commit/4dc4a207918de78c2c5c778388f4e5de18fb75b5))


## v0.5.0 (2022-08-30)

### Chores

- Improve logging and tests :sparkles:
  ([`7d241cf`](https://github.com/AustinBrunkhorst/pysnooz/commit/7d241cf0e528803aa03fd32c65274615fa1bee93))

### Features

- **ci**: Test ci release
  ([`d281979`](https://github.com/AustinBrunkhorst/pysnooz/commit/d281979b0ed7c6ef09b29614ce2ef1263a3c5117))

- **test**: Better logging
  ([`22667f7`](https://github.com/AustinBrunkhorst/pysnooz/commit/22667f72a7f2331dd38d7978d4e2538fe1e88cf3))

### Testing

- Fix ci version
  ([`ff99f91`](https://github.com/AustinBrunkhorst/pysnooz/commit/ff99f913e4da9a262a1206528f7ba4e73aa3c45f))


## v0.3.0 (2022-08-27)

### Documentation

- Update development status to beta
  ([`c881bc2`](https://github.com/AustinBrunkhorst/pysnooz/commit/c881bc2dfd3501e05564c8016cd6830b87e70f95))

### Testing

- Fix loop argument
  ([`b4acf42`](https://github.com/AustinBrunkhorst/pysnooz/commit/b4acf4261d15c5ff1cb10a739cd1580712cca14b))


## v0.2.0 (2022-08-27)

### Chores

- Handle connection exceptions
  ([`d0c261c`](https://github.com/AustinBrunkhorst/pysnooz/commit/d0c261ced5acb3df132b1d9d652784c90723b53a))


## v0.1.0 (2022-08-27)

### Continuous Integration

- Remove argparse
  ([`eaf2793`](https://github.com/AustinBrunkhorst/pysnooz/commit/eaf27936a6ed936aebf9def05ad15254df0b1c88))

- Remove pytransitions
  ([`8f4f8fd`](https://github.com/AustinBrunkhorst/pysnooz/commit/8f4f8fd39fa2e7f13e3a34bb71bb382e07786166))

- Update semantic release config
  ([`e319c36`](https://github.com/AustinBrunkhorst/pysnooz/commit/e319c365bdcb768841b60c80d2e3cbff40a28f3a))

### Documentation

- Add @AustinBrunkhorst as a contributor
  ([`cd208cb`](https://github.com/AustinBrunkhorst/pysnooz/commit/cd208cb8ad534bdcda663997befa08363408b54d))

### Features

- Initial release
  ([`77ec306`](https://github.com/AustinBrunkhorst/pysnooz/commit/77ec306f06cb62df79a35cf81cf69b350ea07801))
