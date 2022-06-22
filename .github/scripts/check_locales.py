#! /usr/bin/env python3
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""
 check_locales.py <locales_path> --ref <locale>
"""

from glob import glob
import argparse
import json
import os
import re
import sys


def parseJsonFiles(base_path, messages, locale):
    """
    Store messages and placeholders. The dictionary id uses the
    format "<relative_file_name>:<messsage_id>".
    """

    file_list = []
    for f in glob(os.path.join(base_path, locale) + "/*.json"):
        parts = f.split(os.sep)
        file_list.append(f)

    for f in file_list:
        file_id = os.path.relpath(f, os.path.join(base_path, locale))
        with open(f) as json_file:
            json_data = json.load(json_file)
            for message_id, message_data in json_data.items():
                text = message_data["message"]
                placeholders = (
                    list(message_data["placeholders"].keys())
                    if "placeholders" in message_data
                    else []
                )
                messages[f"{file_id}:{message_id}"] = {
                    "text": text,
                    "placeholders": placeholders,
                }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "locales_path",
        help="Path to folder including subfolders for all locales",
    )
    parser.add_argument(
        "--ref",
        required=False,
        dest="ref_locale",
        default="en",
        help="Reference locale code (default 'en')",
    )
    args = parser.parse_args()

    # Get a list of files to check (absolute paths)
    base_path = os.path.realpath(args.locales_path)
    reference_locale = args.ref_locale

    # Check if the reference folder exists
    if not os.path.isdir(os.path.join(base_path, reference_locale)):
        sys.exit(
            f"The folder for the reference locale ({reference_locale}) does not exist"
        )
    # Store reference messages and placeholders.
    reference_messages = {}
    parseJsonFiles(base_path, reference_messages, reference_locale)

    # Get path to check_exceptions.json from script path
    exception_file = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "check_exceptions.json")
    )
    if os.path.isfile(exception_file):
        with open(exception_file) as f:
            exceptions = json.load(f)
    else:
        print(f"{exception_file} is missing")
        exceptions = {}

    errors = []
    placeholder_pattern = re.compile("\$([a-zA-Z0-9_@]+)\$")

    # Get a list of locales (subfolders in <locales_path>, exclude hidden folders)
    locales = [
        f
        for f in next(os.walk(base_path))[1]
        if not f.startswith(".") and f != reference_locale
    ]
    locales.sort()

    messages_with_placeholders = {
        k: v["placeholders"]
        for (k, v) in reference_messages.items()
        if v["placeholders"]
    }

    for locale in locales:
        locale_messages = {}
        parseJsonFiles(base_path, locale_messages, locale)

        # Check for missing placeholders
        for message_id, placeholders in messages_with_placeholders.items():
            # Skip if message isn't available in translation
            if message_id not in locale_messages:
                continue

            # Skip if it's a known exception
            if message_id in exceptions["placeholders"].get(locale, {}):
                continue

            l10n_message = locale_messages[message_id]["text"]
            l10n_placeholders = placeholder_pattern.findall(l10n_message)
            if sorted(placeholders) != sorted(l10n_placeholders):
                errors.append(
                    f"{locale}:\n  Placeholder mismatch in {message_id}\n  Text: {l10n_message}"
                )

        for message_id, message_data in locale_messages.items():
            # Check for pilcrows
            l10n_message = message_data["text"]
            if "¶" in message_data["text"]:
                errors.append(
                    f"{locale}:\n  '¶' in {message_id}\n  Text: {l10n_message}"
                )

    if errors:
        print("ERRORS:")
        print("\n".join(errors))
        sys.exit(1)
    else:
        print("No errors found.")


if __name__ == "__main__":
    main()
