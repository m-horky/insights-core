import dataclasses
import json
import pathlib


@dataclasses.dataclass
class Result:
    pass


@dataclasses.dataclass
class SimpleResult(Result):
    data: dict


@dataclasses.dataclass
class ArchiveResult(Result):
    path: pathlib.Path
    content_type: str


@dataclasses.dataclass
class NoResult(Result):
    data: None


class Command:
    def __init__(self):
        import insights.client.auto_config
        import insights.client.client

        config = insights.client.config.InsightsConfig(_print_errors=True)
        config._load_config_file()
        config._imply_options()
        config._validate_options()
        # Ensure logs aren't printed to standard output
        config.silent = True

        # insights.client.client.set_up_logging(config)
        insights.client.auto_config.try_auto_configuration(config)

        self.config = config

    def run(self) -> Result:
        raise NotImplementedError


class CanonicalFacts(Command):
    def run(self) -> SimpleResult:
        import insights.util.canonical_facts

        facts = insights.util.canonical_facts.get_canonical_facts()  # type: dict
        return SimpleResult(facts)


class Advisor(Command):
    def run(self) -> ArchiveResult:
        from insights.client.core_collector import CoreCollector
        from insights.client.archive import InsightsArchive
        from insights.client.collection_rules import InsightsUploadConf

        archive = InsightsArchive(self.config)
        collector = CoreCollector(self.config, archive)

        upload_config = InsightsUploadConf(self.config)
        collector.run_collection(
            rm_conf=upload_config.get_rm_conf(),
            branch_info=self.config.branch_info,
            blacklist_report=upload_config.create_report(),
        )
        collector.done()

        return ArchiveResult(
            path=pathlib.Path(archive.tar_file),
            content_type="application/vnd.redhat.advisor.collection+tgz",
        )
