#! /usr/bin/env python3

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from collections import defaultdict
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
        "--l10n",
        required=True,
        dest="locales_path",
        help="Path to folder including subfolders for all locales",
    )
    parser.add_argument(
        "--ref",
        required=False,
        dest="ref_locale",
        default="en",
        help="Reference locale code (default 'en')",
    )
    parser.add_argument(
        "--dest",
        dest="dest_file",
        help="Save output to file",
    )
    parser.add_argument(
        "--exceptions",
        nargs="?",
        dest="exceptions_file",
        help="Path to JSON exceptions file",
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

    # Load exceptions
    if not args.exceptions_file:
        exceptions = defaultdict(dict)
    else:
        try:
            with open(args.exceptions_file) as f:
                exceptions = json.load(f)
        except Exception as e:
            sys.exit(e)

    errors = defaultdict(list)
    placeholder_pattern = re.compile(r"\$([a-zA-Z0-9_@]+)\$")

    # Get a list of locales (subfolders in <locales_path>, exclude hidden folders)
    locales = [
        f
        for f in next(os.walk(base_path))[1]
        if not f.startswith(".") and f != reference_locale
    ]
    locales.sort()

    # Placeholder names are case insensitive, so transform them to lowercase
    # https://developer.chrome.com/docs/extensions/mv3/i18n-messages/#name
    messages_with_placeholders = {
        k: [p.lower() for p in v["placeholders"]]
        for (k, v) in reference_messages.items()
        if v["placeholders"]
    }

    for locale in locales:
        locale_messages = {}
        parseJsonFiles(base_path, locale_messages, locale)

        # Normalize locale code, e.g. zh_TW => zh-TW
        normalized_locale = locale.replace("_", "-")

        # Check for missing placeholders
        for message_id, placeholders in messages_with_placeholders.items():
            # Skip if message isn't available in translation
            if message_id not in locale_messages:
                continue

            # Skip if it's a known exception
            if message_id in exceptions["placeholders"].get(normalized_locale, {}):
                continue

            l10n_message = locale_messages[message_id]["text"]
            l10n_placeholders = placeholder_pattern.findall(l10n_message)
            # Make placeholders lowercase, and remove duplicates
            l10n_placeholders = list(set(p.lower() for p in l10n_placeholders))

            if sorted(placeholders) != sorted(l10n_placeholders):
                errors[normalized_locale].append(
                    f"Placeholder mismatch in {message_id}\n"
                    f"  Translation: {l10n_message}\n"
                    f"  Reference: {reference_messages[message_id]['text']}"
                )

        ignore_ellipsis = normalized_locale in exceptions["ellipsis"].get(
            "excluded_locales", []
        )
        for message_id, message_data in locale_messages.items():
            l10n_message = message_data["text"]

            # Check for pilcrows
            if "¶" in l10n_message:
                errors[normalized_locale].append(
                    f"'¶' in {message_id}\n  Translation: {l10n_message}"
                )

            # Check for ellipsis
            if not ignore_ellipsis and "..." in l10n_message:
                if message_id in exceptions["ellipsis"].get("locales", {}).get(
                    normalized_locale, []
                ):
                    continue
                errors[normalized_locale].append(
                    f"'...' in {message_id}\n  Translation: {l10n_message}"
                )

    if errors:
        locales = list(errors.keys())
        locales.sort()

        output = []
        total_errors = 0
        for locale in locales:
            output.append(f"\nLocale: {locale} ({len(errors[locale])})")
            total_errors += len(errors[locale])
            for e in errors[locale]:
                output.append(f"\n  {e}")
        output.append(f"\nTotal errors: {total_errors}")

        out_file = args.dest_file
        if out_file:
            print(f"Saving output to {out_file}")
            with open(out_file, "w") as f:
                f.write("\n".join(output))
        # Print errors anyway on screen
        print("\n".join(output))
        sys.exit(1)
    else:
        print("No issues found.")


if __name__ == "__main__":
    main()
