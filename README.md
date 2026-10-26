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
python3 tools/check_game_data.py space-station-14 --apply    # update index.html, the "as of" date, the reaction calculator and the plant list
```

It covers cooking and deep fryer recipes and reactions. New items have no icon until you run `python3 tools/add_icons.py space-station-14`, which needs their textures checked out (it lists the folders to add to the sparse checkout). Slicing, assembled foods, vendor stock and item icons are not regenerated; new items show without an icon until the sprite sheet is rebuilt.

## Chemistry tab

The Chemistry tab comes from the community sheet [SS14 Chemistry for Kobolds](https://docs.google.com/spreadsheets/d/1ExvhhgdQMwxDBjOEoU6wGEOixlurMb_ECHWumff4kIU) by Licks-the-Vials and other Starlight chemists, used with permission. To update it, export the sheet to `data/chemistry-for-kobolds.txt` (each tab as `## Sheet name: X` followed by its rows as CSV) and run `python3 tools/build_chem.py`.
