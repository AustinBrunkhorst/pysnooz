# PySnooz

<p align="center">
  <img src="header.svg" alt="Python Language + Bleak API + SNOOZ White Noise Machine" />
</p>

<p>
  <a href="https://github.com/AustinBrunkhorst/pysnooz/actions?query=workflow%3ACI">
    <img src="https://img.shields.io/github/actions/workflow/status/AustinBrunkhorst/pysnooz/ci.yml?branch=main&label=build&logo=github&style=flat&colorA=000000&colorB=000000" alt="CI Status" >
  </a>
  <a href="https://codecov.io/gh/AustinBrunkhorst/pysnooz">
    <img src="https://img.shields.io/codecov/c/github/AustinBrunkhorst/pysnooz.svg?logo=codecov&logoColor=fff&style=flat&colorA=000000&colorB=000000" alt="Test coverage percentage">
  </a>
  <a href="https://pypi.org/project/pysnooz/">
    <img src="https://img.shields.io/pypi/v/pysnooz.svg?logo=python&logoColor=fff&style=flat&colorA=000000&colorB=000000" alt="PyPI Version">
  </a>
</p>

Control SNOOZ white noise machines with Bluetooth.

## Installation

Install this via pip (or your favourite package manager):

`pip install pysnooz`

## Supported devices

- [SNOOZ Original](https://getsnooz.com/products/snooz-white-noise-machine)
- [SNOOZ Pro](https://getsnooz.com/products/snooz-pro-white-noise-machine)
- [Breez](https://getsnooz.com/products/snooz-breez-smart-bedroom-fan-sound-machine)

## Usage

```python
import asyncio
from datetime import timedelta
from home_assistant_bluetooth import BluetoothServiceInfo
from pysnooz.device import (
  SnoozAdvertisementData,
  SnoozDevice,
  SnoozCommandResultStatus,
  turn_on,
  turn_off,
  set_volume
)

# found with discovery
device_info = BluetoothServiceInfo(...)
advertisement = parse_snooz_advertisement(device_info)

device = SnoozDevice(device_info, advertisement, asyncio.get_event_loop())

# optionally specify a volume to set before turning on
await device.async_execute_command(turn_on(volume=100))

# you can transition volume by specifying a duration
await device.async_execute_command(turn_off(duration=timedelta(seconds=10)))

# you can also set the volume directly
await device.async_execute_command(set_volume(50))

# view the result of a command execution
result = await device.async_execute_command(turn_on())
assert result.status == SnoozCommandResultStatus.SUCCESS
result.duration # how long the command took to complete
```

## Contributors ✨

Thanks goes to these wonderful people ([emoji key](https://allcontributors.org/docs/en/emoji-key)):

<!-- prettier-ignore-start -->
<!-- ALL-CONTRIBUTORS-LIST:START - Do not remove or modify this section -->
<!-- prettier-ignore-start -->
<!-- markdownlint-disable -->
<table>
  <tbody>
    <tr>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/bradleysryder"><img src="https://avatars.githubusercontent.com/u/39577543?v=4?s=80" width="80px;" alt="bradleysryder"/><br /><sub><b>bradleysryder</b></sub></a><br /><a href="https://github.com/AustinBrunkhorst/pysnooz/commits?author=bradleysryder" title="Code">💻</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/mweinelt"><img src="https://avatars.githubusercontent.com/u/131599?v=4?s=80" width="80px;" alt="Martin Weinelt"/><br /><sub><b>Martin Weinelt</b></sub></a><br /><a href="https://github.com/AustinBrunkhorst/pysnooz/commits?author=mweinelt" title="Code">💻</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/epenet"><img src="https://avatars.githubusercontent.com/u/6771947?v=4?s=80" width="80px;" alt="epenet"/><br /><sub><b>epenet</b></sub></a><br /><a href="https://github.com/AustinBrunkhorst/pysnooz/commits?author=epenet" title="Code">💻</a></td>
    </tr>
  </tbody>
</table>

<!-- markdownlint-restore -->
<!-- prettier-ignore-end -->

<!-- ALL-CONTRIBUTORS-LIST:END -->
<!-- prettier-ignore-end -->

This project follows the [all-contributors](https://github.com/all-contributors/all-contributors) specification. Contributions of any kind welcome!

## Credits

This package was created with
[Cookiecutter](https://github.com/audreyr/cookiecutter) and the
[browniebroke/cookiecutter-pypackage](https://github.com/browniebroke/cookiecutter-pypackage)
project template.
