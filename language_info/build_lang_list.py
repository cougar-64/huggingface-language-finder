"""
Builds a dictionary of {iso_code: {"english_names": [...], "native_names": [...]}}
by querying Wikidata for a list of target ISO 639-3 codes. Stored in list_of_languages.py

Usage:
    python build_lang_list.py
"""

import json
import time
import requests

WIKIDATA_SPARQL_URL = "https://query.wikidata.org/sparql"
BATCH_SIZE = 50  # keeps queries small so they run fast and don't time out
HEADERS = {
    "Accept": "application/sparql-results+json",
    # wikidata asks that you identify your script - swap in something real
    "User-Agent": "target-language-dictionary-builder/1.0 (sbird10@byu.edu, Pathsay research project)",
}


def build_query(iso_codes: list) -> str:
    values = " ".join(f'"{code}"' for code in iso_codes)
    return f"""
    SELECT ?iso3 ?lang ?langLabel ?native
           (GROUP_CONCAT(DISTINCT ?altLabel; separator="||") AS ?altLabels)
    WHERE {{
      VALUES ?iso3 {{ {values} }}
      ?lang wdt:P220 ?iso3 .
      OPTIONAL {{ ?lang wdt:P1705 ?native . }}
      OPTIONAL {{
        ?lang skos:altLabel ?altLabel .
        FILTER(LANG(?altLabel) = "en")
      }}
      SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en" . }}
    }}
    GROUP BY ?iso3 ?lang ?langLabel ?native
    """


def query_batch(iso_codes: list) -> list:
    query = build_query(iso_codes)
    response = requests.get(
        WIKIDATA_SPARQL_URL,
        params={"query": query},
        headers=HEADERS,
        timeout=30,
    )
    response.raise_for_status()
    return response.json()["results"]["bindings"]


def build_dictionary(iso_codes: list) -> tuple:
    """Returns (dictionary, not_found_codes)."""
    result = {}
    found_codes = set()

    for i in range(0, len(iso_codes), BATCH_SIZE):
        batch = iso_codes[i : i + BATCH_SIZE]
        print(f"Querying batch {i // BATCH_SIZE + 1} ({len(batch)} codes)...")

        try:
            bindings = query_batch(batch)
        except requests.exceptions.RequestException as e:
            print(f"    batch failed {e}: will retry once")
            time.sleep(2)
            bindings = query_batch(batch)

        for row in bindings:
            iso3 = row["iso3"]["value"]
            english_name = row.get("langLabel", {}).get("value")
            native_name = row.get("native", {}).get("value")
            raw_alt_labels = row.get("altLabels", {}).get("value", "")
            alt_labels = [l for l in raw_alt_labels.split("||") if l]

            entry = result.setdefault(iso3, {"english_names": [], "native_names": []})

            if english_name and english_name not in entry["english_names"]:
                entry["english_names"].append(english_name)
            for alt in alt_labels:
                if alt not in entry["english_names"]:
                    entry["english_names"].append(alt)
            if native_name and native_name not in entry["native_names"]:
                entry["native_names"].append(native_name)

            found_codes.add(iso3)

        time.sleep(1)  # pause between batches, not between individual rows

    not_found = [c for c in iso_codes if c not in found_codes]
    return result, not_found


if __name__ == "__main__":
    ISO_CODES = ['aym', 'kvn', 'haw', 'bel', 'jav', 'pus', 'bho', 'hau', 'Pan', 'ory', 'mai', 'snd', 'sun', 'skr', 'som', 'mag', 'hne', 'zha', 'asm', 'ctg', 'wes', 'run', 'rkt', 'uig', 'tir', 'syl', 'bgc', 'prs', 'kau', 'tgk', 'kik', 'suk', 'mad', 'bal', 'mos', 'sat', 'kas', 'shi', 'umb', 'vah', 'tuk', 'tso', 'vmw', 'heb', 'bjj', 'bns', 'kab', 'mup', 'fuc', 'tat', 'kir', 'sck', 'bew', 'hno', 'mey', 'min', 'fuf', 'uzs', 'shn', 'awa', 'tiv', 'rif', 'din', 'mtr', 'lmn', 'wry', 'bug', 'yao', 'bjn', 'sdh', 'haz', 'dje', 'phr', 'nyn', 'wbr', 'ban', 'bhb', 'glg', 'mui', 'pcc', 'gdx', 'sid', 'swv', 'xog', 'hoj', 'gbm', 'brh', 'ace', 'teo', 'anw', 'bos', 'bfy', 'spv', 'dgo', 'aar', 'rhg', 'bej', 'cjk', 'sus', 'glk', 'cgg', 'fuh', 'tum', 'noe', 'lon', 'kru', 'mzn', 'dyu', 'sgw', 'laj', 'men', 'bci', 'sas', 'bin', 'seh', 'igb', 'ijs', 'mer', 'mnk', 'hay', 'lgg', 'sgc', 'mas', 'ngl', 'hdy', 'zne', 'mni', 'mgh', 'alz', 'nup', 'nah', 'srr', 'mak', 'nus', 'kmb', 'myx', 'gmv', 'tem', 'bbc', 'wal', 'ach', 'dnj', 'igl', 'ndc', 'che', 'any', 'lub', 'brx', 'nym', 'abr', 'sba', 'tig', 'nyy', 'kua', 'bca', 'ven', 'grt', 'bom', 'vls', 'bxk', 'heh', 'bak', 'bod', 'kbr', 'guw', 'dag', 'nyf', 'ajg', 'unr', 'gux', 'cce', 'gog', 'mfe', 'fan', 'urh', 'chv', 'bba', 'kha', 'ada', 'nga', 'sop', 'kbp', 'chw', 'nyo', 'niq', 'tsg', 'its', 'kac', 'idu', 'dga', 'nnb', 'vun', 'yaf', 'ktb', 'nij', 'bum', 'ttj', 'lus', 'gaa', 'bib', 'nia', 'tll', 'xpe', 'led', 'bsq', 'kuj', 'loz', 'yom', 'btg', 'fip', 'aoz', 'kdj', 'gur', 'ish', 'iso', 'ati', 'kri', 'dzo', 'gwr', 'ikw', 'sag', 'gej', 'ady', 'ebu', 'grb', 'khb', 'ukw', 'akl', 'srn', 'sgd', 'goa', 'ijn', 'msb', 'fry', 'sah', 'lia', 'krj', 'cbk', 'mev', 'gxx', 'eke', 'nzi', 'lun', 'klu', 'leb', 'kss', 'toh', 'bas', 'enq', 'lom', 'kno', 'ibg', 'aba', 'kdi', 'arn', 'bjs', 'kqn', 'bkm', 'mgr', 'vai', 'lam', 'mdp', 'abk', 'cyo', 'lok', 'cnh', 'gle', 'kdn', 'njm', 'sur', 'bfq', 'poh', 'acr', 'etu', 'ksd', 'kue', 'stj', 'bpd', 'gud', 'myv', 'yun', 'dua', 'cri', 'knj', 'nzu', 'cac', 'plw', 'jac', 'kjd', 'tqo', 'khz', 'yog', 'agu', 'tbw', 'zun', 'nau', 'mrq', 'kpg', 'pif', 'rap', 'shh']

    dictionary, not_found = build_dictionary(ISO_CODES)

    with open("language_dictionary.json", "w") as f:
        json.dump(dictionary, f, ensure_ascii=False, indent=2)

    print(f"\nResolved {len(dictionary)} of {len(ISO_CODES)} codes.")
    if not_found:
        print(f"{len(not_found)} codes not found on Wikidata, need manual entry")
        for code in not_found:
            print(f" - {code}")