import os
import sys

from insights.client.constants import InsightsConstants
from insights.client.apps.ansible.playbook_verifier import read_playbook_yaml_from_stdin, verify
from insights.client.apps.ansible.playbook_verifier import PlaybookVerificationError


def main():
    playbook = read_playbook_yaml_from_stdin()  # type: dict

    if os.environ.get("SKIP_VERIFY") is not None:
        print(playbook)
        sys.exit(0)

    try:
        verified_playbook = verify(playbook)
    except PlaybookVerificationError as exc:
        sys.stderr.write(exc.message)
        sys.exit(InsightsConstants.sig_kill_bad)

    print(verified_playbook)


if __name__ == "__main__":
    main()
