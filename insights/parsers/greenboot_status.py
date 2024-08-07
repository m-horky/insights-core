"""
GreenbootStatus - Command ``/usr/libexec/greenboot/greenboot-status``
=====================================================================
"""
from insights import parser
from insights.core import LogFileOutput
from insights.core.filters import add_filter
from insights.specs import Specs


_green = "Boot Status is GREEN"
_red = "Boot Status is RED"
_fallback = "FALLBACK BOOT DETECTED"
_nologs = "WARNING: No greenboot logs were found!"
add_filter(Specs.greenboot_status, [_green, _red, _fallback, _nologs])


@parser(Specs.greenboot_status)
class GreenbootStatus(LogFileOutput):
    """
    Collect the filtered output of ``/usr/libexec/greenboot/greenboot-status``.

    The data are lines from the journal log

    Attributes:
        red (bool): True if the system is in RED status.
        green (bool): True if the system is in GREEN status.

    .. note::
        Please refer to the super-class :class:`insights.core.LogFileOutput`
    """
    time_format = "MMM dd HH:mm:ss"


GreenbootStatus.token_scan("green", _green)
GreenbootStatus.token_scan("red", _red)
GreenbootStatus.token_scan("fallback", _fallback)
GreenbootStatus.token_scan("nologs", _nologs)
