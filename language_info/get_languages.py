# This file gets and returns all the language matches in each tier

import re
import unicodedata
from huggingface_hub import hf_hub_download
import json
from pathlib import Path


json_path = Path(__file__).parent / "list_of_languages.json"
with open(json_path, 'r') as f:
    LANGUAGE_DATA = json.load(f)


TIER_ONE = LANGUAGE_DATA["tier_one"]
TIER_TWO = LANGUAGE_DATA["tier_two"]
TIER_THREE = LANGUAGE_DATA["tier_three"]


def normalize(text: str) -> str:
    text = unicodedata.normalize("NFD", text) # normalizes accents (é becomes e and ñ becomes n, etc.)
    text = "".join(c for c in text if unicodedata.category(c) != "Mn") # Strip accents
    return text.lower()



def get_readme_text(repo: str):
    try:
        readme_path = hf_hub_download(repo_id=repo, filename="README.md", repo_type="dataset")
        with open(readme_path, 'r') as f:
            return f.read()
    except Exception:
        return "" # if the dataset doesn't have any readme



def get_language_tag(info):
    language_tag = info.card_data.get("language") if info.card_data else None
    if language_tag is None:
        return []
    if isinstance(language_tag, str):
        return [language_tag]
    return list(language_tag)



def match_languages(iso_code, all_names, readme, repo_name, tagged_langs) -> set: # searches different parts of the hf datasets and looks for language matches
    hits = set() # the variations of the name that was hit (useful for knowing which language names to scrape later)
    if normalize(iso_code) in tagged_langs:
        hits.add(iso_code)
    for n in all_names:
        if normalize(n) in tagged_langs:
            hits.add(n)
        found_in_repo_name = re.search(rf"\b{re.escape(normalize(n))}\b", repo_name)
        if found_in_repo_name:
            hits.add(n)
        found_in_readme = re.search(rf"\b{re.escape(normalize(n))}\b", readme)
        if found_in_readme:
            hits.add(n)

    return hits



def match_metadata(repo_id, info) -> dict:
    readme_text = normalize(get_readme_text(repo_id))
    repo_name_text = normalize(repo_id)
    tagged_langs = [normalize(t) for t in get_language_tag(info)]

    tier_results = {}
    for tier_name, tier_dict in [("tier_one", TIER_ONE), ("tier_two", TIER_TWO), ("tier_three", TIER_THREE)]:
        matches = {}
        for iso_code, names in tier_dict.items():
            all_names = names["english_name"] + names["native_names"]
            hits = match_languages(iso_code, all_names, readme_text, repo_name_text, tagged_langs)
            if hits:
                matches[iso_code] = {"english_name": names["english_name"], "matched_names": sorted(hits)}
        tier_results[tier_name] = matches
    return tier_results