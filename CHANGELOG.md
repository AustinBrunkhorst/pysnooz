# Changelog

<!--next-version-placeholder-->

## v0.8.4 (2023-05-23)
### Fix
* Repair test compatibility with bleak>=0.20.0 ([#9](https://github.com/AustinBrunkhorst/pysnooz/issues/9)) ([`f789d92`](https://github.com/AustinBrunkhorst/pysnooz/commit/f789d9253640a43ca7c8f2f9b8530d017667178c))

## v0.8.3 (2022-10-27)
### Fix
* Use BleakClientWithServiceCache ([`fdd9b32`](https://github.com/AustinBrunkhorst/pysnooz/commit/fdd9b32836ff5320e0bda1f1c7bf60c667bf3145))
* Use BleakClientWithServiceCache ([`e828fe8`](https://github.com/AustinBrunkhorst/pysnooz/commit/e828fe8f72df898ea6c8d1a45180568f0333b14b))

## v0.8.2 (2022-10-10)
### Fix
* Update write_gatt_char for CoreBluetooth backend ([`c1bafc3`](https://github.com/AustinBrunkhorst/pysnooz/commit/c1bafc3c35a1cc445f2078c4d3a00451243e5f25))
* CoreBluetooth backend notifications ([`d476816`](https://github.com/AustinBrunkhorst/pysnooz/commit/d4768164e739393a580296e298f2da8a20b4392b))

## v0.8.1 (2022-10-08)
### Fix
* Add mock device ([`7c62a1b`](https://github.com/AustinBrunkhorst/pysnooz/commit/7c62a1b092b66b182bed0414dd4c7f5a354aaec2))

## v0.8.0 (2022-10-08)
### Feature
* Make loop optional on device ([`09ea58d`](https://github.com/AustinBrunkhorst/pysnooz/commit/09ea58d8b6bfc1e52a86880dc8bfd02ef3828d71))

## v0.7.9 (2022-10-08)
### Fix
* Refactor deprecated bleak disconnect callback ([`2491051`](https://github.com/AustinBrunkhorst/pysnooz/commit/2491051bb197df6ba18218cb2ebfa39bacfd89da))

## v0.7.8 (2022-10-01)
### Fix
* Bump bleak and bleak-retry-connector ([`1c79ae4`](https://github.com/AustinBrunkhorst/pysnooz/commit/1c79ae41ea4a0cc5f6afd6b6aedfa824446c097b))

## v0.7.7 (2022-09-18)
### Fix
* Include mock client in main package ([`27dfbd6`](https://github.com/AustinBrunkhorst/pysnooz/commit/27dfbd6d71d9b2874f417dbd94cb24824ae932e2))

## v0.7.6 (2022-09-14)
### Fix
* Loosen package constraints ([`34f0a14`](https://github.com/AustinBrunkhorst/pysnooz/commit/34f0a145e74ad9c2c7c7a14308061079f93f324f))

## v0.7.5 (2022-09-14)
### Fix
* Bump bleak to 0.17.0 ([`db3a57a`](https://github.com/AustinBrunkhorst/pysnooz/commit/db3a57a706a49cc21294226098ca1cafd4d19689))
* Bump bleak to 0.17.0 ([`010b311`](https://github.com/AustinBrunkhorst/pysnooz/commit/010b31172c936626db8d4c3dc0269d01057c10ab))

## v0.7.4 (2022-09-08)
### Fix
* Bump bluetooth packages ([`595e575`](https://github.com/AustinBrunkhorst/pysnooz/commit/595e57564857cbbb0000c19dc7746b0ae9264677))

### Documentation
* Update README ([`828ce0d`](https://github.com/AustinBrunkhorst/pysnooz/commit/828ce0d02d6e3fe5c0959a02855585a73b997246))

## v0.7.3 (2022-08-31)
### Fix
* Improve resilience for exceptions ([`349ad59`](https://github.com/AustinBrunkhorst/pysnooz/commit/349ad59dacbfa7220bc5fe05197262e67c0959e6))

### Documentation
* Update .all-contributorsrc [skip ci] ([`b943305`](https://github.com/AustinBrunkhorst/pysnooz/commit/b94330500816d7423d11cde4ade6e4de64acc2cf))
* Update README.md [skip ci] ([`f11d8fd`](https://github.com/AustinBrunkhorst/pysnooz/commit/f11d8fdb65f4e6e17f67c2aa717a5e5bf0607306))

## v0.7.2 (2022-08-31)
### Fix
* Issue URL + sleep on write retry ([`bc57d51`](https://github.com/AustinBrunkhorst/pysnooz/commit/bc57d510a3288ca234390583d71d2e1f02c55bc6))

## v0.7.1 (2022-08-30)
### Fix
* Add missing f-string ([`8637d3b`](https://github.com/AustinBrunkhorst/pysnooz/commit/8637d3b00d4307461d5229e4b822895daa4896de))

## v0.7.0 (2022-08-30)
### Feature
* **docs:** Add initial usage ([`1d3f439`](https://github.com/AustinBrunkhorst/pysnooz/commit/1d3f43937493573c6979d01f91b01f7998d55edd))

## v0.6.2 (2022-08-30)
### Fix
* **logs:** Add logs + api tests ([`c587f81`](https://github.com/AustinBrunkhorst/pysnooz/commit/c587f81357f1a70ce46af118c77b65cb1b9ab568))

## v0.6.1 (2022-08-30)
### Fix
* **log:** Use formatted message for status change ([`4dc4a20`](https://github.com/AustinBrunkhorst/pysnooz/commit/4dc4a207918de78c2c5c778388f4e5de18fb75b5))

## v0.6.0 (2022-08-30)
### Feature
* **test:** Better logging ([`22667f7`](https://github.com/AustinBrunkhorst/pysnooz/commit/22667f72a7f2331dd38d7978d4e2538fe1e88cf3))

## v0.5.0 (2022-08-30)
### Feature
* **ci:** Test ci release ([`d281979`](https://github.com/AustinBrunkhorst/pysnooz/commit/d281979b0ed7c6ef09b29614ce2ef1263a3c5117))

## v0.1.0 (2022-08-27)
### Feature
* Initial release ([`77ec306`](https://github.com/AustinBrunkhorst/pysnooz/commit/77ec306f06cb62df79a35cf81cf69b350ea07801))

### Documentation
* Add @AustinBrunkhorst as a contributor ([`cd208cb`](https://github.com/AustinBrunkhorst/pysnooz/commit/cd208cb8ad534bdcda663997befa08363408b54d))
