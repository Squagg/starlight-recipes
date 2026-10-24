# Starlight Recipes

Recipe and drink guide for the Starlight Space Station 14 server.

Live at https://starlight-recipes.pages.dev

Built by Squagg with help from Claude (Anthropic's AI assistant), which wrote much of the code and recipe data processing.

## Updating the recipe data

`tools/check_game_data.py` compares the site against Starlight's game files and lists cooking recipes and drink reactions that were added, removed or changed:

```
git clone --depth 1 --filter=blob:none --sparse https://github.com/ss14Starlight/space-station-14
git -C space-station-14 sparse-checkout set Resources/Prototypes Resources/Locale/en-US
pip install pyyaml
python3 tools/check_game_data.py space-station-14            # report only
python3 tools/check_game_data.py space-station-14 --apply    # update index.html and the "as of" date
```

It covers cooking recipes and reactions. Slicing, assembled foods, vendor stock and item icons are not regenerated; new items show without an icon until the sprite sheet is rebuilt.
