import optparse
import sys
import logging
import os.path

import insights
import insights.client
import insights.client.archive
import insights.client.collection_rules
import insights.client.core_collector
import insights.client.config
from insights.client import InsightsClient, utilities

logger = logging.getLogger(__name__)

ERR_RUNTIME_ERROR = 1
ERR_PRECONDITION_FAILED = 5


class Archive:
    """Data archive.

    This object keeps the minimal API compatibility with module
    `insights.client.archive.InsightsArchive` required to perform a collection.
    """

    def __init__(self, archive_directory):
        self.archive_dir = archive_directory

    @property
    def tmp_dir(self):
        return os.path.dirname(self.archive_dir)

    @property
    def archive_name(self):
        return os.path.basename(self.archive_dir)

    def create_archive_dir(self):
        return self.archive_dir

    def add_metadata_to_archive(self, metadata, meta_path):
        """Include metadata in the archive collection.

        :type metadata: str
        :type meta_path: str
        """
        in_archive_path = os.path.join(self.archive_dir, meta_path)  # type: str
        os.makedirs(os.path.dirname(in_archive_path), exist_ok=True, mode=0o700)
        with open(in_archive_path, "w") as f:
            f.write(metadata)

def set_up_logging():
    """Configure logging."""
    config = insights.client.config.InsightsConfig(_print_errors=True)
    config._load_config_file()
    insights.client.client.set_up_logging(config)


def build_client_and_config():
    """Configure logging and the client configuration."""
    config = insights.client.config.InsightsConfig(_print_errors=True)
    config._load_config_file()
    config._imply_options()
    config._validate_options()
    config.silent = True
    config.keep_archive = True
    config.no_upload = True
    config.output_dir = True
    # Can be removed after RHINENG-6982, insights-core#4009 are solved:
    config.core_collect = True

    client = InsightsClient(config)
    insights.client.auto_config.try_auto_configuration(config)
    logger.debug("Core path: %s", os.path.dirname(insights.__path__[0]))
    logger.debug("Core version: %s", client.version())

    return client, config


def advisor_collect(args):
    """Run the main Advisor collection.

    :type args: list[str]
    """
    _, config = build_client_and_config()

    parser = optparse.OptionParser()
    parser.add_option("--archive", help="collection directory")
    parser.add_option("--group", help="before collection, update group")
    parser.add_option("--display-name", help="during collection, include display name in metadata")
    parser.add_option("--ansible-host", help="during collection, include ansible host in metadata")
    options, _ = parser.parse_args(args)

    # This is required during registration. Since the host doesn't exist in
    # Inventory yet, display name and ansible hostname are included in archive
    # metadata as `/display_name` and `/ansible_host` files.
    config.display_name = options.display_name
    config.ansible_host = options.ansible_host

    if options.group is not None:
        tags = utilities.get_tags() or {}
        if options.group == "":
            logger.debug("Deleting group from tags file.")
            del tags["group"]
        else:
            logger.debug("Updating group in tags file to '{value}'.".format(value=options.group))
            tags["group"] = options.group
        utilities.write_tags(tags)

    archive = Archive(archive_directory=options.archive)
    collector = insights.client.core_collector.CoreCollector(config, archive)
    upload_config = insights.client.collection_rules.InsightsUploadConf(config)

    logger.debug("Starting collection.")
    try:
        collector.run_collection(
            rm_conf=upload_config.get_rm_conf(),
            branch_info=config.branch_info,
            blacklist_report=upload_config.create_report(),
        )
        collector.done()
        logger.debug("Collection finished")
    except Exception as exc:
        logger.error(exc)
        print("Error: Collection failed: {exc}.".format(exc=exc))
        sys.exit(ERR_RUNTIME_ERROR)


def advisor_diagnosis(args):
    print("Error: Not implemented.", file=sys.stderr)
    sys.exit(ERR_RUNTIME_ERROR)


def advisor_check_results(args):
    print("Error: Not implemented.", file=sys.stderr)
    sys.exit(ERR_RUNTIME_ERROR)


def advisor_show_results(args):
    print("Error: Not implemented.", file=sys.stderr)
    sys.exit(ERR_RUNTIME_ERROR)


def advisor_list_specs(args):
    print("Error: Not implemented.", file=sys.stderr)
    sys.exit(ERR_RUNTIME_ERROR)


def advisor_manifest(args):
    print("Error: Not implemented.", file=sys.stderr)
    sys.exit(ERR_RUNTIME_ERROR)


def advisor_build_packagecache(args):
    print("Error: Not implemented.", file=sys.stderr)
    sys.exit(ERR_RUNTIME_ERROR)


def advisor_validate(args):
    print("Error: Not implemented.", file=sys.stderr)
    sys.exit(ERR_RUNTIME_ERROR)


def compliance_collect(args):
    print("Error: Not implemented.", file=sys.stderr)
    sys.exit(ERR_RUNTIME_ERROR)


def malware_collect(args):
    print("Error: Not implemented.", file=sys.stderr)
    sys.exit(ERR_RUNTIME_ERROR)


def main():
    if len(sys.argv) < 2:
        print("Error: No command specified.", file=sys.stderr)
        sys.exit(ERR_PRECONDITION_FAILED)
    if len(sys.argv) < 3:
        print("Error: No subcommand specified.", file=sys.stderr)
        sys.exit(ERR_PRECONDITION_FAILED)

    set_up_logging()

    command = (sys.argv[1], sys.argv[2])  # type: tuple[str, str]
    logger.debug("Executing: command=%s args=%s", command, sys.argv[3:])

    if command == ("advisor", "collect"):
        return advisor_collect(args=sys.argv[3:])
    if command == ("advisor", "check-results"):
        return advisor_check_results(args=sys.argv[3:])
    if command == ("advisor", "show-results"):
        return advisor_show_results(args=sys.argv[3:])
    if command == ("advisor", "list-specs"):
        return advisor_list_specs(args=sys.argv[3:])
    if command == ("advisor", "diagnosis"):
        return advisor_diagnosis(args=sys.argv[3:])
    if command == ("advisor", "manifest"):
        return advisor_manifest(args=sys.argv[3:])
    if command == ("advisor", "build-packagecache"):
        return advisor_build_packagecache(args=sys.argv[3:])
    if command == ("advisor", "validate"):
        return advisor_validate(args=sys.argv[3:])

    if command == ("compliance", "collect"):
        return compliance_collect(args=sys.argv[3:])
    if command == ("malware", "collect"):
        return malware_collect(args=sys.argv[3:])

    print("Error: Unknown command: {command}.".format(command=" ".join(command)), file=sys.stderr)
    sys.exit(ERR_PRECONDITION_FAILED)


if __name__ == "__main__":
    main()
