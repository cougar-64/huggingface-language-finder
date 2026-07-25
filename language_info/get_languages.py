

import re
import unicodedata
from huggingface_hub import dataset_info, hf_hub_download


def get_languages(repo: str):
    info = dataset_info(repo)
    license_tag = info.card_data.get("language") if info.card_data else None