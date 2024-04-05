import enum
import logging
import sys

import insights.client.auto_config
import insights.client.client
import insights.client.config

logger = logging.getLogger(__name__)


class AppService(enum.Enum):
    INGRESS = "INGRESS"
    INVENTORY = "INVENTORY"


class AppReturnType(enum.Enum):
    SIMPLE = "SIMPLE"
    ARCHIVE = "ARCHIVE"


class AppFlag(object):
    def __init__(
        self,
        *,
        name,  # type: str
        help,  # type: str
        type=None,  # type: str | None
        action=None,  # type: str | None
    ):
        """An `argparse` flag.

        All the arguments are passed into `add_argument()` of the app command parser.

        Please note that the `type` argument will be passed to `eval()` by the client.

        :param name: The flag name.
        :param help: The flag help.
        :param type: The flag type. Defaults to `str`.
        :param action: The flag action. Defaults to `store`.
        """
        self.name = name
        self.help = help
        self.type = type if type is not None else "str"
        self.action = action if action is not None else "store"

    def to_dict(self):
        # type: () -> dict
        return {
            "name": self.name,
            "help": self.help,
            "type": self.type,
            "action": self.action,
        }


class AppCommand(object):
    def __init__(
        self,
        name,  # type: str
        help,  # type: str
        flags=None,  # type: list[AppFlag] | None
    ):
        self.name = name
        self.help = help
        self.flags = flags if flags is not None else []

    def to_dict(self):
        # type: () -> dict
        return {
            "name": self.name,
            "help": self.help,
            "flags": [f.to_dict() for f in self.flags],
        }


class App(object):
    def __init__(
        self,
        *,
        name,  # type: str
        help,  # type: str
        service,  # type: AppService
        return_type,  # type: AppReturnType
        commands=None,  # type: list[AppCommand] | None
    ):
        self.name = name
        self.help = help
        self.service = service
        self.return_type = return_type
        self.commands = commands if commands is not None else []

    def to_dict(self):
        # type: () -> dict
        return {
            "name": self.name,
            "help": self.help,
            "service": self.service.name,
            "return_type": self.return_type.name,
            "commands": [c.to_dict() for c in self.commands],
        }


APPLICATIONS = [
    App(
        name="checkin",
        help="scan the system for canonical facts and upload the results to Insights",
        service=AppService.INVENTORY,
        return_type=AppReturnType.SIMPLE,
        commands=[],
    ),
    App(
        name="compliance",
        help="scan the system and upload the results to Insights Compliance",
        service=AppService.INGRESS,
        return_type=AppReturnType.ARCHIVE,
        commands=[
            AppCommand(
                name="run",
                help="run the collection",
                flags=[],
            ),
            AppCommand(
                name="policy",
                help="manage the host's compliance policy",
                flags=[
                    AppFlag(name="--list", help="list existing policies", type="bool", action="store_true",),
                    AppFlag(name="--get", help="display the host's compliance policy", type="bool", action="store_true",),
                    AppFlag(name="--set", help="assign the")
                ],
            )
        ]
    ),
]


class Core(object):
    def __init__(self):
        config = insights.client.config.InsightsConfig(_print_errors=True)
        config._load_config_file()
        config._imply_options()
        config._validate_options()

        insights.client.client.set_up_logging(config)
        insights.client.auto_config.try_auto_configuration(config)

        self.config = config


def main():
    # type: () -> None

    # Create the Core reference. It instantiates the Config object and sets up logging.
    core = Core()

    command = sys.argv[1] if len(sys.argv) > 1 else "help"  # type: str


if __name__ == "__main__":
    main()
