"""
Schema-level detection: looks at dataset's config names, column
names, and feature structure WITHOUT downloading any actual data rows.

uses load_dataset_builder(), which only reads the dataset's metadata/schema.
"""

from language_info.get_languages import normalize
import re
from datasets import load_dataset_builder, get_dataset_config_names


LANG_COLUMN_HINTS = {"language", "lang", "src_lang", "tgt_lang", "source_lang", "target_lang"}


def build_lookup(lang_data: dict) -> dict:
    """
    Flattens all three tiers into one lookup: normalized names/iso -> (iso_code, tier).
    Used so we can check "does this string refer to one of our target languages"
    in O(1) regardless of what tier its in.
    """
    lookup = {}
    for tier_name, tier_dict in lang_data.items():
        for iso_code, names in tier_dict.items():
            lookup[normalize(iso_code)] = iso_code, tier_name
            for n in names["english_names"] + names["native_names"]:
                lookup[normalize(n)] = iso_code, tier_name

    return lookup



def check_config_names(repo_id: str, lookup: dict) -> dict:
    """Checks whether config names correspond to target language."""
    matches = {}
    try:
        configs = get_dataset_config_names(repo_id)
    except Exception:
        return matches # some datasets have no explicit configs, or the call fails

    for config in configs:
        norm_config = normalize(config)
        if norm_config in lookup:
            iso_code, tier = lookup[norm_config]
            matches.setdefault(iso_code, {"tier": tier, "matched_via": set()})
            matches[iso_code]["matched_via"].add(f"config:{config}")

    return matches



def check_feature_schema(repo_id: str, lookup: dict, config_name: str = None) -> dict:
    """
    inspects the feature schema for:
        - column names that hint at language (language, lang, src_lang, etc.)
        - nested dict-like Translation features whose keys are language codes
    Does NOT read the language values from a plain "language" column --
    that requires touching actual row data, which belongs in the content-sampling step.
    """
    matches = {}
    lang_columns_found = []
    try:
        builder = load_dataset_builder(repo_id, config_name) if config_name else load_dataset_builder(repo_id)
        features = builder.info.features
    except Exception:
        return matches, lang_columns_found

    if features is None:
        return matches, lang_columns_found

    for col_name, feature in features.items():
        norm_col = normalize(col_name)

        # Case 1: column name itself hints that it holds language info
        if norm_col in LANG_COLUMN_HINTS or "lang" in norm_col:
            lang_columns_found.append(col_name)

        # Case 2: nested translation-style dict, e.g. Translation(languages=["en", "bam"])
        feature_str = str(feature)
        lang_codes_in_feature = re.findall(r"'([a-z]{2,3})'", feature_str)
        for code in lang_codes_in_feature:
            norm_code = normalize(code)
            if norm_code in lookup:
                iso_code, tier = lookup[norm_code]
                matches.setdefault(iso_code, {"tier": tier, "matched_via": set()})
                matches[iso_code]["matched_via"].add(f"feature_key:{code}")

    return matches, lang_columns_found



def match_schema(repo_id: str, language_data: dict) -> dict:
    """
    Runs a full schema-level check for one dataset.
    Returns: {iso_code: {"tier": ..., "matched_via": [...]}}, plus a separate
    list of columns that look language-related but need content sampling to confirm.
    """
    lookup = build_lookup(language_data)
    all_matches = {}
    needs_content_check = set()

    config_matches = check_config_names(repo_id, lookup)
    for iso_code, data in config_matches.items():
        all_matches.setdefault(iso_code, {"tier": data["tier"], "matched_via": set()})
        all_matches[iso_code]["matched_via"] |= data["matched_via"]

    try:
        configs = get_dataset_config_names(repo_id)
    except Exception:
        configs = [None] # fall back to default config

    for config in configs:
        feature_matches, lang_cols = check_feature_schema(repo_id, lookup, config)
        needs_content_check.update(lang_cols)
        for iso_code, data in feature_matches.items():
            all_matches.setdefault(iso_code, {"tier": data["tier"], "matched_via": set()})
            all_matches[iso_code]["matched_via"] |= data["matched_via"]

    # converts sets to sorted lists for clean printing/serialization
    for iso_code in all_matches:
        all_matches[iso_code]["matched_via"] = sorted(all_matches[iso_code]["matched_via"])

    return all_matches, sorted(needs_content_check)



if __name__ == "__main__":
    import json

    with open("language_info/list_of_languages.json", 'r') as f:
        language_data = json.load(f)

    repo_id = "facebook/flores" # replace with a REAL dataset for testing!
    matches, needs_content_check = match_schema(repo_id, language_data)

    print(json.dumps(matches, indent=2, ensure_ascii=False))
    if needs_content_check:
        print(f"\nColumns that look language-related but need content sampling to confirm: {needs_content_check}")