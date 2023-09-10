# CHANGELOG



## v0.9.0 (2023-09-10)

### Feature

* feat: support for breez and pro devices (#14)

* test: improve coverage

* test: update pyproject.toml for tests

* test: add device properties for testing

* test: add coverage for mock clients

* test: mock client handles disconnect properly

* test: states are copied in mock clients

* docs: add supported devices, update usage

---------

Co-authored-by: github-actions &lt;github-actions@github.com&gt; ([`3b823c8`](https://github.com/AustinBrunkhorst/pysnooz/commit/3b823c8272864352220838ccbddb97655afb311c))


## v0.8.6 (2023-08-30)

### Chore

* chore: update other python references ([`a59a48f`](https://github.com/AustinBrunkhorst/pysnooz/commit/a59a48fd4b62f5cab22018d23a0f0791f128db92))

* chore: ci uses python 3.11 ([`94fcf4c`](https://github.com/AustinBrunkhorst/pysnooz/commit/94fcf4cf1f2803cc4bf0341ab39772261cf1b400))

* chore: update to python 3.11 ([`c0cc57f`](https://github.com/AustinBrunkhorst/pysnooz/commit/c0cc57f22b14f2ebbe7b00e3952f4e9b57af4d1a))

### Ci

* ci: add contents write permission ([`c8e1a46`](https://github.com/AustinBrunkhorst/pysnooz/commit/c8e1a46d4b72b4b50cf1a7b0f4bed9d8c82b73a2))

* ci: revert to python 3.10 ([`270dd16`](https://github.com/AustinBrunkhorst/pysnooz/commit/270dd168257df3edfdf9a6123abf3dd86155f2cf))

* ci: fix semantic release toml definitions ([`1dba5db`](https://github.com/AustinBrunkhorst/pysnooz/commit/1dba5dbdd88b9b64dfcd0ef6ffd0b0467a4b4348))

* ci: update semantic release ([`6fd209e`](https://github.com/AustinBrunkhorst/pysnooz/commit/6fd209ec54279b51c18b8b507ad63db7af5c2076))

### Documentation

* docs: add epenet as a contributor for code (#13)

* docs: update README.md [skip ci]

* docs: update .all-contributorsrc [skip ci]

---------

Co-authored-by: allcontributors[bot] &lt;46447321+allcontributors[bot]@users.noreply.github.com&gt; ([`8a4e372`](https://github.com/AustinBrunkhorst/pysnooz/commit/8a4e37232c258ecbc10773e295b0e3019c73e4f7))

### Fix

* fix: unsubscribe from events after disconnect ([`14ef0b4`](https://github.com/AustinBrunkhorst/pysnooz/commit/14ef0b48a1b7da04517246c7b3612814e7a98572))


## v0.8.5 (2023-05-24)

### Chore

* chore: update build status badge

[skipci] ([`4efb497`](https://github.com/AustinBrunkhorst/pysnooz/commit/4efb497a2af8fda7540ddd94d853f885293f12d3))

### Documentation

* docs: add mweinelt as a contributor for code (#12)

* docs: update README.md [skip ci]

* docs: update .all-contributorsrc [skip ci]

---------

Co-authored-by: allcontributors[bot] &lt;46447321+allcontributors[bot]@users.noreply.github.com&gt; ([`5b291df`](https://github.com/AustinBrunkhorst/pysnooz/commit/5b291df26551d5da7137351ab0d3ddae4cf71be8))

### Fix

* fix: race condition during disconnect (#7) ([`d1ac03f`](https://github.com/AustinBrunkhorst/pysnooz/commit/d1ac03fa16a5d17a9b9a7252d6e6baaadc5a7768))


## v0.8.4 (2023-05-23)

### Chore

* chore: update dependencies, target python 3.10 (#10)

* chore: update dependencies, target python 3.10

* chore: run black formatter ([`ac2ea3f`](https://github.com/AustinBrunkhorst/pysnooz/commit/ac2ea3f36252bb5540a4e44dfb42aa49476dea59))

### Fix

* fix: repair test compatibility with bleak&gt;=0.20.0 (#9)

With the bleak 0.20.0 release the rssi and metadata attributes on the
BLEDevice object became properties, that need to be initialized in the
constructor. This broke parts of the test suite, that this changeset
fixes.

Closes: #8 ([`f789d92`](https://github.com/AustinBrunkhorst/pysnooz/commit/f789d9253640a43ca7c8f2f9b8530d017667178c))


## v0.8.3 (2022-10-27)

### Ci

* ci: temporarily disable broken windows tests ([`bf8a259`](https://github.com/AustinBrunkhorst/pysnooz/commit/bf8a2596347360f45a6bf2648556c373caa1b968))

* ci: update action dependency ([`7893894`](https://github.com/AustinBrunkhorst/pysnooz/commit/7893894f0189097eda81f9fdf18f7cf420189780))

* ci: update pre-commit/action to v3.0.0 ([`9fff0a9`](https://github.com/AustinBrunkhorst/pysnooz/commit/9fff0a96d42e98510a1001acbdadc9581b2bcf0f))

### Fix

* fix: use BleakClientWithServiceCache ([`fdd9b32`](https://github.com/AustinBrunkhorst/pysnooz/commit/fdd9b32836ff5320e0bda1f1c7bf60c667bf3145))

* fix: use BleakClientWithServiceCache ([`e828fe8`](https://github.com/AustinBrunkhorst/pysnooz/commit/e828fe8f72df898ea6c8d1a45180568f0333b14b))

### Unknown

* Revert &#34;fix: use BleakClientWithServiceCache&#34;

This reverts commit e828fe8f72df898ea6c8d1a45180568f0333b14b. ([`e73cead`](https://github.com/AustinBrunkhorst/pysnooz/commit/e73cead7fa0470a6db5d5632fe958fd31f3f83c7))

* Merge branch &#39;main&#39; of https://github.com/AustinBrunkhorst/pysnooz ([`f10f898`](https://github.com/AustinBrunkhorst/pysnooz/commit/f10f898a872a4c8a8952c92b784d81c60c8430d5))


## v0.8.2 (2022-10-10)

### Fix

* fix: update write_gatt_char for CoreBluetooth backend ([`c1bafc3`](https://github.com/AustinBrunkhorst/pysnooz/commit/c1bafc3c35a1cc445f2078c4d3a00451243e5f25))

* fix: CoreBluetooth backend notifications ([`d476816`](https://github.com/AustinBrunkhorst/pysnooz/commit/d4768164e739393a580296e298f2da8a20b4392b))

### Unknown

* Merge branch &#39;main&#39; of https://github.com/AustinBrunkhorst/pysnooz ([`458d6a9`](https://github.com/AustinBrunkhorst/pysnooz/commit/458d6a9001445a01c9f986dd9a88fcaed02885cb))

* Merge branch &#39;main&#39; of https://github.com/AustinBrunkhorst/pysnooz ([`3263ca2`](https://github.com/AustinBrunkhorst/pysnooz/commit/3263ca2580d07d1e72d833c013dbe5acd66d9a0f))


## v0.8.1 (2022-10-08)

### Fix

* fix: add mock device ([`7c62a1b`](https://github.com/AustinBrunkhorst/pysnooz/commit/7c62a1b092b66b182bed0414dd4c7f5a354aaec2))

### Unknown

* Merge branch &#39;main&#39; of https://github.com/AustinBrunkhorst/pysnooz ([`6eecce2`](https://github.com/AustinBrunkhorst/pysnooz/commit/6eecce23cb31d233e9fa48aba9e3be7f8081d5b5))


## v0.8.0 (2022-10-08)

### Feature

* feat: make loop optional on device ([`09ea58d`](https://github.com/AustinBrunkhorst/pysnooz/commit/09ea58d8b6bfc1e52a86880dc8bfd02ef3828d71))

### Unknown

* Merge branch &#39;main&#39; of https://github.com/AustinBrunkhorst/pysnooz ([`b3af8c2`](https://github.com/AustinBrunkhorst/pysnooz/commit/b3af8c2b433c2ba59c06e26fcfa7f25f17c399ce))


## v0.7.9 (2022-10-08)

### Fix

* fix: refactor deprecated bleak disconnect callback
chore: add subscription method ([`2491051`](https://github.com/AustinBrunkhorst/pysnooz/commit/2491051bb197df6ba18218cb2ebfa39bacfd89da))


## v0.7.8 (2022-10-01)

### Fix

* fix: bump bleak and bleak-retry-connector ([`1c79ae4`](https://github.com/AustinBrunkhorst/pysnooz/commit/1c79ae41ea4a0cc5f6afd6b6aedfa824446c097b))

### Unknown

* Merge branch &#39;main&#39; of https://github.com/AustinBrunkhorst/pysnooz ([`a638d65`](https://github.com/AustinBrunkhorst/pysnooz/commit/a638d6506e7564d006392164f24e9f55f185f9d7))


## v0.7.7 (2022-09-18)

### Fix

* fix: include mock client in main package ([`27dfbd6`](https://github.com/AustinBrunkhorst/pysnooz/commit/27dfbd6d71d9b2874f417dbd94cb24824ae932e2))

### Test

* test: include mock client to main package ([`ce898fa`](https://github.com/AustinBrunkhorst/pysnooz/commit/ce898fabcd5584211b9866ad567cdb770d970c44))

### Unknown

* Merge branch &#39;main&#39; of https://github.com/AustinBrunkhorst/pysnooz ([`50b8807`](https://github.com/AustinBrunkhorst/pysnooz/commit/50b8807c8f627058f210db07b69fe9796a99dd54))

* Merge branch &#39;main&#39; of https://github.com/AustinBrunkhorst/pysnooz ([`bcf6443`](https://github.com/AustinBrunkhorst/pysnooz/commit/bcf644391abbd1caf17924d5b5d6ec38d7f506b8))


## v0.7.6 (2022-09-14)

### Fix

* fix: loosen package constraints ([`34f0a14`](https://github.com/AustinBrunkhorst/pysnooz/commit/34f0a145e74ad9c2c7c7a14308061079f93f324f))

### Unknown

* Merge branch &#39;main&#39; of https://github.com/AustinBrunkhorst/pysnooz ([`b1e337c`](https://github.com/AustinBrunkhorst/pysnooz/commit/b1e337cd3fbc0a24468f5622b0a919473f9ebef1))


## v0.7.5 (2022-09-14)

### Fix

* fix: bump bleak to 0.17.0 ([`db3a57a`](https://github.com/AustinBrunkhorst/pysnooz/commit/db3a57a706a49cc21294226098ca1cafd4d19689))

* fix: Bump bleak to 0.17.0 ([`010b311`](https://github.com/AustinBrunkhorst/pysnooz/commit/010b31172c936626db8d4c3dc0269d01057c10ab))

### Unknown

* Merge branch &#39;main&#39; of https://github.com/AustinBrunkhorst/pysnooz ([`a40f2eb`](https://github.com/AustinBrunkhorst/pysnooz/commit/a40f2eb17afd08382f9c1b54a64ff5c5ca06ed00))

* Merge branch &#39;main&#39; of https://github.com/AustinBrunkhorst/pysnooz ([`bbaefa4`](https://github.com/AustinBrunkhorst/pysnooz/commit/bbaefa45a8bce43c020ce373338993979534f7d3))


## v0.7.4 (2022-09-08)

### Documentation

* docs: update README
[skip ci] ([`828ce0d`](https://github.com/AustinBrunkhorst/pysnooz/commit/828ce0d02d6e3fe5c0959a02855585a73b997246))

### Fix

* fix: bump bluetooth packages ([`595e575`](https://github.com/AustinBrunkhorst/pysnooz/commit/595e57564857cbbb0000c19dc7746b0ae9264677))

### Unknown

* Merge branch &#39;main&#39; of https://github.com/AustinBrunkhorst/pysnooz ([`520cfec`](https://github.com/AustinBrunkhorst/pysnooz/commit/520cfec70fed49c11d2084ff7b6240756c0bbcdd))


## v0.7.3 (2022-08-31)

### Documentation

* docs: update .all-contributorsrc [skip ci] ([`b943305`](https://github.com/AustinBrunkhorst/pysnooz/commit/b94330500816d7423d11cde4ade6e4de64acc2cf))

* docs: update README.md [skip ci] ([`f11d8fd`](https://github.com/AustinBrunkhorst/pysnooz/commit/f11d8fdb65f4e6e17f67c2aa717a5e5bf0607306))

### Fix

* fix: improve resilience for exceptions ([`349ad59`](https://github.com/AustinBrunkhorst/pysnooz/commit/349ad59dacbfa7220bc5fe05197262e67c0959e6))

### Unknown

* Merge branch &#39;main&#39; of https://github.com/AustinBrunkhorst/pysnooz ([`6289d40`](https://github.com/AustinBrunkhorst/pysnooz/commit/6289d40c5b88139026f3e241046e18dc9fbf2ff2))

* Merge pull request #2 from AustinBrunkhorst/all-contributors/add-bradleysryder

docs: add bradleysryder as a contributor for code ([`7840bf4`](https://github.com/AustinBrunkhorst/pysnooz/commit/7840bf49bae6dfff5d7c82ee530211d86c7a2e39))


## v0.7.2 (2022-08-31)

### Fix

* fix: issue URL + sleep on write retry ([`bc57d51`](https://github.com/AustinBrunkhorst/pysnooz/commit/bc57d510a3288ca234390583d71d2e1f02c55bc6))

### Unknown

* Merge branch &#39;main&#39; of https://github.com/AustinBrunkhorst/pysnooz ([`04fdb84`](https://github.com/AustinBrunkhorst/pysnooz/commit/04fdb8489941f2b4c7144f2d4b90748f3f3478cc))

* doc: update readme ([`4e8232f`](https://github.com/AustinBrunkhorst/pysnooz/commit/4e8232f2e4c4d220906857e44a60e88781b89bf0))


## v0.7.1 (2022-08-30)

### Chore

* chore: update readme ([`fe687ef`](https://github.com/AustinBrunkhorst/pysnooz/commit/fe687ef645d14c88c76136eb9160cb43d01b0547))

### Fix

* fix: add missing f-string ([`8637d3b`](https://github.com/AustinBrunkhorst/pysnooz/commit/8637d3b00d4307461d5229e4b822895daa4896de))

### Unknown

* Merge branches &#39;main&#39; and &#39;main&#39; of https://github.com/AustinBrunkhorst/pysnooz ([`788b104`](https://github.com/AustinBrunkhorst/pysnooz/commit/788b104702eb5ab9f7064d0e176f6645a4cd652e))


## v0.7.0 (2022-08-30)

### Feature

* feat(docs): add initial usage ([`1d3f439`](https://github.com/AustinBrunkhorst/pysnooz/commit/1d3f43937493573c6979d01f91b01f7998d55edd))

### Test

* test(api): fix mock warnings ([`3b03e74`](https://github.com/AustinBrunkhorst/pysnooz/commit/3b03e74ea57a74fb919ef6540ac8b5dcd8039fe9))

* test(api): use magic mock instead of async mock ([`ae5194e`](https://github.com/AustinBrunkhorst/pysnooz/commit/ae5194ea14b07041bdf24e79f547d1aa0a23afec))

* test(advertisement): add advertisement tests ([`9dd5b81`](https://github.com/AustinBrunkhorst/pysnooz/commit/9dd5b815ab9db54fdca2a104e1a15a9dc4bb3bc3))

### Unknown

* Merge branches &#39;main&#39; and &#39;main&#39; of https://github.com/AustinBrunkhorst/pysnooz ([`00d48db`](https://github.com/AustinBrunkhorst/pysnooz/commit/00d48db362f006d3862c828fabd6e313dddd62f4))


## v0.6.2 (2022-08-30)

### Fix

* fix(logs): add logs + api tests ([`c587f81`](https://github.com/AustinBrunkhorst/pysnooz/commit/c587f81357f1a70ce46af118c77b65cb1b9ab568))

### Unknown

* Merge branch &#39;main&#39; of https://github.com/AustinBrunkhorst/pysnooz ([`143c441`](https://github.com/AustinBrunkhorst/pysnooz/commit/143c4417d7e2da73dd743bacc1ef5dcc4940ee74))


## v0.6.1 (2022-08-30)

### Fix

* fix(log): use formatted message for status change ([`4dc4a20`](https://github.com/AustinBrunkhorst/pysnooz/commit/4dc4a207918de78c2c5c778388f4e5de18fb75b5))

### Unknown

* Merge branch &#39;main&#39; of https://github.com/AustinBrunkhorst/pysnooz ([`bac88e9`](https://github.com/AustinBrunkhorst/pysnooz/commit/bac88e96d4b62fb0e13331e791e1153081e0ab34))


## v0.6.0 (2022-08-30)

### Feature

* feat(test): better logging ([`22667f7`](https://github.com/AustinBrunkhorst/pysnooz/commit/22667f72a7f2331dd38d7978d4e2538fe1e88cf3))

### Unknown

* Merge branch &#39;main&#39; of https://github.com/AustinBrunkhorst/pysnooz ([`19e5333`](https://github.com/AustinBrunkhorst/pysnooz/commit/19e5333c55f4a265dd2a1e99e5896067d017fc78))


## v0.5.0 (2022-08-30)

### Chore

* chore: improve logging and tests :sparkles: ([`7d241cf`](https://github.com/AustinBrunkhorst/pysnooz/commit/7d241cf0e528803aa03fd32c65274615fa1bee93))

### Feature

* feat(ci): test ci release ([`d281979`](https://github.com/AustinBrunkhorst/pysnooz/commit/d281979b0ed7c6ef09b29614ce2ef1263a3c5117))

### Test

* test: fix ci version ([`ff99f91`](https://github.com/AustinBrunkhorst/pysnooz/commit/ff99f913e4da9a262a1206528f7ba4e73aa3c45f))


## v0.3.0 (2022-08-27)

### Documentation

* docs: update development status to beta ([`c881bc2`](https://github.com/AustinBrunkhorst/pysnooz/commit/c881bc2dfd3501e05564c8016cd6830b87e70f95))

### Test

* test: fix loop argument ([`b4acf42`](https://github.com/AustinBrunkhorst/pysnooz/commit/b4acf4261d15c5ff1cb10a739cd1580712cca14b))


## v0.2.0 (2022-08-27)

### Chore

* chore: handle connection exceptions ([`d0c261c`](https://github.com/AustinBrunkhorst/pysnooz/commit/d0c261ced5acb3df132b1d9d652784c90723b53a))


## v0.1.0 (2022-08-27)

### Ci

* ci: update semantic release config ([`e319c36`](https://github.com/AustinBrunkhorst/pysnooz/commit/e319c365bdcb768841b60c80d2e3cbff40a28f3a))

* ci: remove argparse ([`eaf2793`](https://github.com/AustinBrunkhorst/pysnooz/commit/eaf27936a6ed936aebf9def05ad15254df0b1c88))

* ci: remove pytransitions ([`8f4f8fd`](https://github.com/AustinBrunkhorst/pysnooz/commit/8f4f8fd39fa2e7f13e3a34bb71bb382e07786166))

### Documentation

* docs: add @AustinBrunkhorst as a contributor ([`cd208cb`](https://github.com/AustinBrunkhorst/pysnooz/commit/cd208cb8ad534bdcda663997befa08363408b54d))

### Feature

* feat: initial release ([`77ec306`](https://github.com/AustinBrunkhorst/pysnooz/commit/77ec306f06cb62df79a35cf81cf69b350ea07801))

### Unknown

* remove python versions ([`2a6fc63`](https://github.com/AustinBrunkhorst/pysnooz/commit/2a6fc633044a53bd83d5880b7162381f16c31747))

* initial commit ([`c269c46`](https://github.com/AustinBrunkhorst/pysnooz/commit/c269c46eaab8a92c7a095dd78eff3cd6eb54fee5))

* Initial commit ([`417f645`](https://github.com/AustinBrunkhorst/pysnooz/commit/417f645b7494ce88001d1491c5644ea1acc03390))
