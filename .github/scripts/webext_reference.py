#! /usr/bin/env python3

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from collections import defaultdict
from pathlib import Path
import argparse
import json
import os
import re
import sys


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--path",
        required=True,
        dest="ref_path",
        help="Path to folder with reference JSON files",
    )
    args = parser.parse_args()

    # Get a list of files to check (absolute paths)
    search_path = Path(args.ref_path)
    file_paths = search_path.glob(f"**/*.json")

    errors = defaultdict(list)
    placeholder_pattern = re.compile("\$([a-zA-Z0-9_@]+)\$")

    for fn in file_paths:
        filename = os.path.basename(fn)
        with open(fn, "r") as f:
            json_content = json.load(f)
            for id, message in json_content.items():
                text = message["message"]
                # Check for incorrect characters
                if "'" in text:
                    errors[filename].append(
                        "Use an apostrophe ’ instead of straight quotes '"
                    )
                if "..." in text:
                    errors[filename].append(
                        "Use the ellipsis character … instead of 3 dots ..."
                    )

                # Check placeholders
                placeholders = placeholder_pattern.findall(text)
                placeholders = list(set([p.lower() for p in placeholders]))
                placeholders.sort()

                if placeholders:
                    if "placeholders" not in message:
                        errors[filename].append(
                            f"Section 'placeholders' missing in {id}"
                        )
                    else:
                        defined_placeholders = [
                            p.lower() for p in message["placeholders"].keys()
                        ]
                        defined_placeholders.sort()

                        for p in placeholders:
                            if p not in defined_placeholders:
                                errors[filename].append(
                                    f"Placeholder {p} is used in string '{id}' but not defined in the placeholders section"
                                )

    if errors:
        for fn, fn_errors in errors.items():
            print(f"File: {fn}")
            for e in fn_errors:
                print(f"  {e}")
        sys.exit()
    else:
        print("No issues found.")


if __name__ == "__main__":
    main()
