MAX_BODY_CHARS = 12000
LOCATE_IDLE_SECONDS = 2

# categorize.py
CATEGORIZE_IDLE_SECONDS = 2
CATEGORY_MODEL = "MoritzLaurer/deberta-v3-large-zeroshot-v2.0"
CATEGORY_THRESHOLD = 0.5    # keep every category scoring at least this
CATEGORY_TEXT_CHARS = 1500  # body chars added after title + summary (model reads ~512 tokens)
GPU_MEMORY_GB = 14          # VRAM cap for this process
