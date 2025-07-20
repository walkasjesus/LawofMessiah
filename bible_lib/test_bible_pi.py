from bible_lib import BibleFactory
from bible_lib import BibleBooks
from bible_lib.bible_api.api_bibles import ApiBibles

# Load API key and default Bible ID from settings.py
api_key = None
default_bible_id = None
with open("bible_lib/settings.py") as f:
    for line in f:
        if "API_KEY" in line:
            api_key = line.split("=")[1].strip().strip('"').strip("'")
        if "DEFAULT_BIBLE_ID" in line:
            default_bible_id = line.split("=")[1].strip().strip('"').strip("'")

bible_factory = BibleFactory(api_key)
bible = bible_factory.create(default_bible_id)
text = bible.verse(BibleBooks.John, 3, 16)
print(text)