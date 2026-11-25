"""Apply the project's build policy to a complete Bandit JSON report."""

import json
import sys
from pathlib import Path


def evaluate(report):
    if report["errors"]:
        print("Bandit could not analyse every input file.")
        return 2
    blocked = 0
    for finding in report["results"]:
        blocking = (
            finding["issue_severity"] == "HIGH"
            and finding["issue_confidence"] == "HIGH"
        )
        blocked += blocking
        label = "BLOCK" if blocking else "WARNING"
        print(
            f'{label} {finding["test_id"]} '
            f'{finding["filename"]}:{finding["line_number"]} '
            f'{finding["issue_severity"]}/{finding["issue_confidence"]}'
        )
    print(f'{len(report["results"])} findings, {blocked} blocking.')
    return int(blocked > 0)


if __name__ == "__main__":
    sys.exit(evaluate(json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))))
