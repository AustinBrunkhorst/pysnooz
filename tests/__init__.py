"""Unit test package for pysnooz."""

from pysnooz.model import SnoozDeviceModel

SUPPORTED_MODELS = [m for m in SnoozDeviceModel if m != SnoozDeviceModel.UNSUPPORTED]
