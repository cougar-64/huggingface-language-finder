"""
Content-sampling fallback: streams a small sample of the dataset's actual text
and runs it through a language-ID model.

IMPORTANT SCOPING NOTE:
py3langid only supports 97 languages total. Of the 370ish target languages we need,
only a small subset will overlap with what it can actually detect. This module is
explicit about that -- it reports "not checkable via content sampling" for target
languages outside the LID model's coverage, rather than silently returning a
false "not found".
"""

import json
import unicodedata
import pycountry
import py3langid as langid
from datasets import load_dataset, get_dataset_config_names

SAMPLE_SIZE = 100 # rows to sample per config/split
MIN_TEXT_LENGTH = 20 # skips short strings likely to be IDs/labels, not real text
MIN_CONFIDENCE = 0.6 # py3langid normalized confidence threshold to count a hit
MIN_HITS_TO_REPORT = 3 # requires multiple matching samples, not a single fluke

_identifier = langid.langid.LanguageIdentifier.from_pickled_model(
    langid.langid.MODEL_FILE, norm_probs = True
)



def get_lid_supported_iso3_codes() -> set:
    """Returns a set of iso 639-3 codes py3langid can actually detect"""
    supported = set()
    for code_2letter in _identifier.nb_classes:
        lang = pycountry.languages.get(alpha_2=code_2letter)
        if lang:
            supported.add(lang.alpha_3)
    return supported



def get_checkable_target_languages(language_data: dict) -> tuple:
    """
    Splits target languages into (checkable, not_checkable) based on
    whether py3langid's model actually covers them.
    """
    lid_supported = get_lid_supported_iso3_codes()
    all_target_isos = set()
    for tier_dict in language_data.values():
        all_target_isos.update(tier_dict.keys())

    checkable = all_target_isos & lid_supported
    not_checkable = all_target_isos - lid_supported
    return checkable, not_checkable



def find_text_columns(example: dict) -> list:
    """Hueristic: string-valued fields above a minimum length are probably real text."""
    text_columns = []
    for col, value in example.items():
        if isinstance(value, str) and len(value.strip()) >= MIN_TEXT_LENGTH:
            text_columns.append(col)
    return text_columns



def sample_and_detect(repo_id: str, config_names: str = None, split: str = "train") -> dict:
    """
    Streams a small sample from one config/split, runs LID on any text columns found and
    tallies hits per detected iso-639 code.
    :returns: {iso_code: {"hits": int, "avg_confidence": float}}
    """
    tally = {} # iso_code -> list of confidence scores
    try:
        ds = load_dataset(repo_id, config_names, split=split, streaming=True)
    except Exception:
        return tally # split/config might not exist, or data needs auth, etc.

    text_columns = None
    checked = 0

    for example in ds:
        if checked >= SAMPLE_SIZE:
            break

        if text_columns is None:
            text_columns = find_text_columns(example)
            if not text_columns:
                break # no usable text columns found, nothing to sample

        for col in text_columns:
            value = example.get(col)
            if not isinstance(value, str) or len(value.strip()) < MIN_TEXT_LENGTH:
                continue

            lang_2letter, confidence = _identifier.classify(value)
            if confidence < MIN_CONFIDENCE:
                continue

            lang_obj = pycountry.languages.get(alpha_2=lang_2letter)
            if not lang_obj:
                continue

            iso3 = lang_obj.alpha_3
            tally.setdefault(iso3, []).append(float(confidence))
        checked +=1

    results = {}
    for iso3, scores in tally.items():
        if len(scores) >= MIN_HITS_TO_REPORT:
            results[iso3] = {
                "hits": len(scores),
                "avg_confidence": round(sum(scores) / len(scores), 3),
            }
    return results



def match_content(repo_id: str, language_data: dict) -> dict:
    """
    Runs content sampling across all configs of a dataset.
    Returns:
         {
        "matches": {iso_code: {"hits": int, "avg_confidence": float, "tier": str}},
        "not_checkable": [iso_codes in target list that LID can't detect at all],
        }
    """
    checkable, not_checkable = get_checkable_target_languages(language_data)

    iso_to_tier = {}
    for tier_name, tier_dict in language_data.items():
        for iso in tier_dict:
            iso_to_tier[iso] = tier_name

    try:
        configs = get_dataset_config_names(repo_id)
    except Exception:
        configs = [None]

    all_matches = {}
    for config in configs:
        config_results = sample_and_detect(repo_id, config)
        for iso3, data in config_results.items():
            if iso3 not in checkable:
                continue # only report matches for language LID can actually detect
            if iso3 in all_matches:
                # merge across configs -- keep the stronger evidence
                all_matches[iso3]["hits"] += data["hits"]
            else:
                all_matches[iso3] = {**data, "tier": iso_to_tier.get(iso3, "unknown")}

    return {
        "matches": all_matches,
        "not_checkable": sorted(not_checkable)
    }



if __name__ == "__main__":
    with open("list_of_languages.json", "r") as f:
        language_data = json.load(f)

    repo_id = "some/dataset" # REPLACE WITH A REAL REPO ID TO TEST!!!!
    result = match_content(repo_id, language_data)

    print("Matches found via content sampling:")
    print(json.dumps(result["matches"], indent=2, ensure_ascii=False))
    print(f"\n{len(result['not_checkable'])} targets are NOT checkable via "
          f" Content sampling (outside the LID model's coverage) -- rely on metadata/schema for these.")