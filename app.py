"""Compatible station launcher; implementation lives in morsepi.app."""
import importlib
import sys

if __name__ == "__main__":
    from morsepi.app import main
    main()
else:
    sys.modules[__name__] = importlib.import_module("morsepi.app")
