# PySnooz

<p align="center">
  <img src="header.svg" alt="Python Language + Bleak API + SNOOZ White Noise Machine" />
</p>

<p>
  <a href="https://github.com/AustinBrunkhorst/pysnooz/actions?query=workflow%3ACI">
    <img src="https://img.shields.io/github/workflow/status/AustinBrunkhorst/pysnooz/CI/main?label=build&logo=github&style=flat&colorA=000000&colorB=000000" alt="CI Status" >
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

## Usage

```python
import asyncio
from datetime import timedelta
from bleak.backends.client import BLEDevice
from pysnooz.device import SnoozDevice
from pysnooz.commands import SnoozCommandResultStatus, turn_on, turn_off, set_volume

# found with discovery
ble_device = BLEDevice(...)
token = "deadbeef"

device = SnoozDevice(ble_device, token, asyncio.get_event_loop())

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
  <tr>
    <td align="center"><a href="https://github.com/bradleysryder"><img src="https://avatars.githubusercontent.com/u/39577543?v=4?s=80" width="80px;" alt=""/><br /><sub><b>bradleysryder</b></sub></a><br /><a href="https://github.com/AustinBrunkhorst/pysnooz/commits?author=bradleysryder" title="Code">💻</a></td>
  </tr>
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
