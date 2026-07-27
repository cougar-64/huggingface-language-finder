"""
This script takes a single huggingface dataset and returns all language matches
    for all Pathsay languages that don't have enough data (40,000 is the threshold).
It will use a dictionary that matches iso codes to all potential spellings (with
    accents, variations of the name, native name) of the target language in order to
    cast the largest net.
The languages are split by priority: 1, 2, 3, as determined by Dr. Richardson and
    myself (Sam Bird). This program's return will tell you the priority of the language.
    Per Dr. Richardson, we are only focusing on priorities 1 and 2 right now.
*NOTE* This script does NOT give you actual data to use - it just tells you which languages
    are available. Due to the discretionary structure of hugging face datasets, it is
    impossible to write a script that will successfully extract languages from ANY
    dataset. Individual scripts will have to be written for each dataset (but not each language).

USAGES:
    python scrape_hf_dataset.py dataset_name
    python scrape_hf_dataset.py dataset_name
"""


import argparse
from urllib.parse import urlparse
from huggingface_hub import dataset_info
from language_info import get_languages



def normalize_repo_id(link: str) -> str:
    link = link.strip()
    if not link.startswith('http'):
        return link

    path = urlparse(link).path
    parts = [p for p in path.split("/") if p] # drop empty strings from leading/trailing slashes

    if "dataset" not in parts:
        raise ValueError(f"doesn't look like a Hugging Face dataset: {link}")

    idx = parts.index("datasets")
    repo_parts = parts[idx + 1 : idx + 3] # namespace + name, ignore everything else
    if len(repo_parts) < 2:
        raise ValueError(f"Error: Could not extract namespace/name from: {link}")

    return "/".join(repo_parts)



def check_license(repo: str):
    info = dataset_info(repo)
    license_tag = info.card_data.get("license") if info.card_data else None
    if license_tag:
        return license_tag
    return "Unknown"



def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("repository", help="Hugging Face ID or full URL")
    args = parser.parse_args()
    repo = normalize_repo_id(args.repository)
    license = check_license(repo)
    print(f"License is {license} Proceed?")
    proceed = input("y/n")
    if proceed == 'n':
        print(f"dataset rejected. Reason: license={license}")
        ... # log dataset in simple SQL database
        print("dataset logged in database")
        return
    languages = get_languages.get_language_tag(repo)




if __name__ == "__main__":
    main()