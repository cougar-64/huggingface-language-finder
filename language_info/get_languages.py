# This file gets and returns all the language matches in each tier

import re
import unicodedata
from huggingface_hub import dataset_info, hf_hub_download
from list_of_languages import TIER_ONE, TIER_TWO, TIER_THREE



def normalize(text: str) -> str:
    text = unicodedata.normalize("NFD", text) # normalizes accents (é becomes e and ñ becomes n, etc.)
    text = "".join(c for c in text if unicodedata.category(c) != "Mn") # Strip accents
    return text.lower()



def get_readme_text(repo: str):
    try:
        readme_path = hf_hub_download(repo_id="repo_id", filename="README", repo_type="dataset")
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



def match_languages(iso_code, all_names, readme, repo_name, tagged_langs, eng_name) -> dict: # searches different parts of the hf datasets and looks for language matches
    ret_dict = {} # eng_name: specifically how it was found (helpful for scraping the dataset later)
    if normalize(iso_code) in tagged_langs:
        ret_dict[eng_name] = iso_code
    for n in all_names:
        if normalize(n) in tagged_langs:
            ret_dict[eng_name] = n
            break

    found_in_repo_name = any(
        re.search(rf"\b{re.escape(normalize()")
    )



def match_metadata(repo_id, info) -> list:
    result_tier_one = []
    result_tier_two = []
    result_tier_three = []


    readme_text = normalize(get_readme_text(repo_id))
    repo_name_text = normalize(repo_id)
    tagged_langs = [normalize(t) for t in get_language_tag(info)]

    for iso_code, names in TIER_ONE.itmes():
        all_names = names["english_name"] + names["native_names"] # multiple variations for one language, multiple languages not in all_names