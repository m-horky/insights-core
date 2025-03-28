#!/usr/bin/env python
import argparse
import logging
import warnings

from insights.ocp import analyze


log = logging.getLogger(__name__)

banner = """
Openshift Configuration Explorer

Tutorial: https://github.com/RedHatInsights/insights-core/blob/master/docs/notebooks/Parsr%20Query%20Tutorial.ipynb

conf is the top level configuration. Use conf.get_keys() to see first level keys.

Available Predicates
    lt, le, eq, gt, ge

    isin, contains

    startswith, endswith, matches

    ieq, icontains, istartswith, iendswith

Available Operators
    ~ (not)
    | (or)
    & (and)

Example
    api = conf.where("kind", "KubeAPIServer")
    latest = api.status.latestAvailableRevision.value
    api.status.nodeStatuses.where("currentRevision", ~eq(latest))
"""


def parse_args():
    p = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    p.add_argument("archives", nargs="+", help="Archive or directory to analyze.")
    p.add_argument("-D", "--debug", help="Verbose debug output.", action="store_true")
    p.add_argument("--exclude", default="*.log", help="Glob patterns to exclude separated by commas")
    return p.parse_args()


def parse_exclude(exc):
    return [e.strip() for e in exc.split(",")]


def main():
    warnings.warn(
        "This '{0}' is deprecated and will be removed in {1}.".format('insights.ocpshell', '3.6.0'),
        DeprecationWarning,
        stacklevel=2,
    )
    args = parse_args()
    archives = args.archives
    if args.debug:
        logging.basicConfig(level=logging.DEBUG)

    excludes = parse_exclude(args.exclude) if args.exclude else ["*.log"]

    conf = analyze(archives, excludes)  # noqa F841 / unused var

    # import all the built-in predicates
    from insights.parsr.query import (lt, le, eq, gt, ge, isin, contains,  # noqa: F401,F403
            startswith, endswith, ieq, icontains, istartswith, iendswith,
            matches, make_child_query)
    q = make_child_query

    import IPython
    from traitlets.config.loader import Config

    ns = dict(locals())
    ns["analyze"] = analyze
    ns["ALL"] = None
    ns["ANY"] = None

    IPython.core.completer.Completer.use_jedi = False
    c = Config()
    c.TerminalInteractiveShell.banner1 = banner
    IPython.start_ipython([], user_ns=ns, config=c)


if __name__ == "__main__":
    main()
