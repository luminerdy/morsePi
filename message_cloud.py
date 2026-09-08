"""Temporary bridge for pre-package station updaters and imports."""
import importlib
import sys

sys.modules[__name__] = importlib.import_module("morsepi.messaging.message_cloud")
