include("$(PORT_DIR)/boards/manifest.py")

# Board-specific Python libraries (frozen into firmware)
freeze("$(BOARD_DIR)/modules")
