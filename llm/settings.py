MAX_BODY_CHARS = 12000
LOCATE_IDLE_SECONDS = 2

# categorize.py
CATEGORIZE_IDLE_SECONDS = 2
CATEGORY_MODEL = "BAAI/bge-small-en-v1.5"  # small embedding model, ~30 ms per article on CPU
CATEGORY_BATCH_SIZE = 32    # articles embedded together
CATEGORY_TEXT_CHARS = 1000  # body chars added after title + summary (model reads 256 tokens)
CATEGORY_MIN_SCORE = 0.59   # best similarity below this -> 'Other'
CATEGORY_MARGIN = 0.01      # also keep categories this close to the best one
CATEGORY_MAX_LABELS = 2     # at most this many categories per article
