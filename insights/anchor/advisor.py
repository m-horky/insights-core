import os
import logging
import pathlib

import insights.client.archive
import insights.client.auto_config
import insights.client.client
import insights.client.collection_rules
import insights.client.core_collector


logger = logging.getLogger(__name__)


class Command:
    config: insights.client.config.InsightsConfig

    def __init__(self):
        config = insights.client.config.InsightsConfig(_print_errors=True)
        config._load_config_file()
        config._imply_options()
        config._validate_options()
        config.silent = True

        insights.client.client.set_up_logging(config)
        insights.client.auto_config.try_auto_configuration(config)

        self.config = config

    def run(self) -> insights.client.archive.InsightsArchive:
        archive = insights.client.archive.InsightsArchive(self.config)
        collector = insights.client.core_collector.CoreCollector(self.config, archive)
        upload_config = insights.client.collection_rules.InsightsUploadConf(self.config)

        logger.debug("Starting collection")
        collector.run_collection(
            rm_conf=upload_config.get_rm_conf(),
            branch_info=self.config.branch_info,
            blacklist_report=upload_config.create_report(),
        )
        collector.done()
        return archive


def main(archive_path: pathlib.Path) -> None:
    if not archive_path.parent.is_dir():
        raise RuntimeError(f"Directory for archive '{archive_path!s}' does not exist.")
    if archive_path.exists():
        raise RuntimeError(f"Archive path '{archive_path!s}' already exists.")

    try:
        archive: insights.client.archive.InsightsArchive = Command().run()
    except Exception as exc:
        raise RuntimeError(f"Could not create archive: {exc!s}")

    try:
        logger.debug("Moving archive '{}' into '{}'.".format(archive.tar_file, archive_path))
        os.rename(archive.tar_file, archive_path)
    except OSError as exc:
        raise RuntimeError(f"Could not move archive '{archive_path!s}': {exc!s}")


if __name__ == '__main__':
    if (ARCHIVE_PATH := os.getenv('ARCHIVE_PATH')) is None:
        raise RuntimeError("ARCHIVE_PATH was not specified.")

    main(archive_path=pathlib.Path(ARCHIVE_PATH))
