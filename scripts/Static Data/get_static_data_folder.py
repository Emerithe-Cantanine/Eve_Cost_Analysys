import os
import re

def get_folder_name():
    base_dir = r"F:\Eve Cost Analysis\scripts\Static Data"  # change this to the parent directory

    pattern = re.compile(r"eve-online-static-data-(\d+)-yaml")

    versions = []

    for name in os.listdir(base_dir):
        match = pattern.match(name)
        if match:
            version_number = int(match.group(1))
            versions.append((version_number, name))

    if not versions:
        raise Exception("No matching folders found!")

    # Get the folder with the highest number
    latest_folder = max(versions)[1]
    latest_path = os.path.join(base_dir, latest_folder).removesuffix(".zip")

    return latest_path