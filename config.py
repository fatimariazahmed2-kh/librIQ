import os

# Base Directories
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
ASSETS_DIR = os.path.join(BASE_DIR, "assets")

# Ensure required directories exist
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(ASSETS_DIR, exist_ok=True)

# Database File Path
DB_PATH = os.path.join(DATA_DIR, "library.db")

# -------------------------------------------------------------
# COLOR PALETTE (Gentle Pink, Blue, Sea Green, Silver, White)
# -------------------------------------------------------------
COLOR_PRIMARY_SEA_GREEN = "#00BFA5"      # Main buttons, accents
COLOR_SEA_GREEN_HOVER   = "#00897B"

COLOR_PINK              = "#EC407A"      # Highlights, stats cards, warning elements
COLOR_PINK_HOVER        = "#D81B60"

COLOR_BLUE              = "#1976D2"      # Links, active tabs, secondary buttons
COLOR_BLUE_HOVER        = "#1565C0"

COLOR_SILVER_BG         = "#F4F6F9"      # Main window background
COLOR_CARD_BG           = "#FFFFFF"      # Cards & panels background
COLOR_SIDEBAR_BG        = "#1E293B"      # Dark slate background for premium sidebar navigation

# Text Colors
COLOR_TEXT_DARK         = "#1F2937"
COLOR_TEXT_MUTED        = "#6B7280"
COLOR_TEXT_LIGHT        = "#FFFFFF"

# Border & Table Colors
COLOR_BORDER            = "#E5E7EB"
COLOR_TABLE_ROW_ALT     = "#F9FAFB"
COLOR_TABLE_HOVER       = "#F3F4F6"

# -------------------------------------------------------------
# FONTS CONFIGURATION
# -------------------------------------------------------------
FONT_FAMILY = "Segoe UI"
FONT_HEADER = (FONT_FAMILY, 20, "bold")
FONT_SUBHEADER = (FONT_FAMILY, 14, "bold")
FONT_BODY = (FONT_FAMILY, 12, "normal")
FONT_SMALL = (FONT_FAMILY, 10, "normal")