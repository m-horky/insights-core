import json
import logging
import sys


logger = logging.getLogger(__name__)


class Reporter:
    @classmethod
    def result(cls, data):
        # type: (dict) -> None
        """Return a result of the command to the Client."""
        print(json.dumps(data, indent=4, sort_keys=True))
        return

    @classmethod
    def status(cls, message):
        # type: (str) -> None
        """Report a status message from the Core."""
        print(message, file=sys.stderr)
        return

    @classmethod
    def exit(cls, *, ok):
        """Quit."""
        sys.exit(0 if ok else 1)


class Core(object):
    def __init__(self):
        import insights.client.auto_config
        import insights.client.client

        config = insights.client.config.InsightsConfig(_print_errors=True)
        config._load_config_file()
        config._imply_options()
        config._validate_options()
        # Ensure logs aren't printed to the standard output.
        config.silent = True

        insights.client.client.set_up_logging(config)
        insights.client.auto_config.try_auto_configuration(config)

        self.config = config

    def checkin(self):
        # type: () -> None
        """Collect ultralight with canonical facts."""
        import insights.util.canonical_facts
        import insights.client.utilities

        try:
            Reporter.result(insights.util.canonical_facts.get_canonical_facts())
        except Exception as exc:
            Reporter.result({"insights_id": insights.client.utilities.generate_machine_id()})
            Reporter.status("Could not collect canonical facts: {exc}.".format(exc=exc))

    def advisor(self):
        # type: () -> None
        """Collect advisor data."""
        import insights.client.client
        from insights.client.core_collector import CoreCollector
        from insights.client.archive import InsightsArchive
        from insights.client.collection_rules import InsightsUploadConf

        # Ensure the Advisor tar file does not get deleted when it is garbage collected.
        self.config.keep_archive = True

        try:
            archive = InsightsArchive(self.config)
            collector = CoreCollector(self.config, archive)
            upload_config = InsightsUploadConf(self.config)
            collector.run_collection(
                rm_conf=upload_config.get_rm_conf(),
                branch_info=self.config.branch_info,
                blacklist_report=upload_config.create_report(),
            )
            collector.done()
            archive.cleanup_tmp()
            Reporter.result({
                "payload": archive.archive_stored,
                "content_type": "application/vnd.redhat.advisor.collection+tgz"
            })
        except Exception as exc:
            Reporter.status("Could not collect Advisor data: {exc}.".format(exc=exc))

    def compliance(self):
        # type: () -> None
        """Collect compliance data."""
        import insights.client.apps.compliance
        # Ensure the Compliance tar file does not get deleted when it is garbage collected.
        self.config.keep_archive = True

        try:
            compliance_client = insights.client.apps.compliance.ComplianceClient(config=self.config)
            _, content_type = compliance_client.oscap_scan()
            Reporter.result({"payload": compliance_client.archive.archive_stored, "content_type": content_type})
        except Exception as exc:
            Reporter.status("Could not collect Compliance data: {exc}.".format(exc=exc))


def main():
    # type: () -> None

    # Create the core reference.
    # This instantiates the Config object and sets up logging.
    core = Core()

    commands = {
        "checkin": core.checkin,
        "advisor": core.advisor,
        "compliance": core.compliance,
    }  # type: dict[str, "Callable[[], None]"]

    command = sys.argv[1] if len(sys.argv) > 1 else "help"  # type: str

    if command == "help":
        Reporter.result({"commands": [c for c in commands.keys()]})
        Reporter.exit(ok=True)

    if command not in commands:
        logger.debug("Unknown command '{}'".format(command))
        Reporter.status("Unknown command '{}'".format(command))
        Reporter.exit(ok=False)

    logger.debug("Running command '{command}'".format(command=command))
    Reporter.status("Running '{command}'".format(command=command))
    commands[command]()
    logger.debug("Command '{command}' completed.".format(command=command))

    Reporter.exit(ok=True)


if __name__ == "__main__":
    main()
