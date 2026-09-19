

"""
Actual settings are in foodanalyzer.config. Used to make "import config" from the repo root
"""


from foodanalyzer.config import Settings, get_settings, reset_settings_cache

__all__ = ["Settings", "get_settings", "reset_settings_cache"]
