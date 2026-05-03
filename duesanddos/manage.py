#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""

import os
import sys


def main():
    """Run administrative tasks."""
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "duesanddos.settings")

    # Monkey-patch Django for Python 3.14 compatibility in tests
    if "test" in sys.argv:
        try:
            from django.template.context import BaseContext

            def patched_copy(self):
                cls = self.__class__
                result = cls.__new__(cls)
                for key, value in self.__dict__.items():
                    setattr(result, key, value)
                if hasattr(self, "dicts"):
                    result.dicts = self.dicts[:]
                return result

            BaseContext.__copy__ = patched_copy
        except (ImportError, AttributeError):
            pass
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
