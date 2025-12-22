# Death Guard Catalogue Viewer

An interactive Streamlit application to explore and visualize Warhammer 40k Death Guard army catalogue data from BattleScribe files.

## Features

- **Overview Dashboard**: Quick stats and metrics about the catalogue
- **Units Browser**: View all available units with filtering options
- **Unit Definitions**: Detailed unit information including costs and categories
- **Profiles & Stats**: Combat statistics and characteristics
- **Rules & Abilities**: Special rules with searchable descriptions
- **Linked Catalogues**: View external catalogue dependencies
- **Global Search**: Search across all data types

## Installation

This project uses [UV](https://github.com/astral-sh/uv) for dependency management.

1. Sync dependencies (UV will automatically create a venv):
```bash
uv sync
```

That's it! UV will handle everything else.

## Usage

Run the Streamlit app with UV:
```bash
uv run streamlit run death_guard_viewer.py
```

Or activate the venv and run directly:
```bash
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
streamlit run death_guard_viewer.py
```

The app will automatically open in your default web browser at `http://localhost:8501`

## Navigation

- Use the **sidebar** to select different views
- Each view has its own **search and filter** options
- Click on **expandable sections** to see detailed information
- **Export data** to CSV where available

## Data Structure

The viewer parses the following from the `.cat` XML files:

- **Entry Links**: Unit references in the catalogue
- **Shared Selections**: Actual unit definitions with costs
- **Profiles**: Combat stats (Movement, Toughness, Save, etc.)
- **Rules**: Special abilities and army mechanics
- **Catalogue Links**: References to other catalogues

## Tips

- Use the Search view for quick lookups across all data
- Filter out hidden units in the Units view for a cleaner list
- Legends units are marked in their names
- Export profiles to CSV for external analysis

## Development

The viewer is designed to be easily extended. Key functions:

- `parse_catalogue()`: Parses the XML and caches the result
- `extract_entry_links()`: Extracts unit references
- `extract_shared_selections()`: Extracts unit definitions
- `extract_profiles()`: Extracts stat profiles
- `extract_rules()`: Extracts special rules

You can add new extraction functions or modify existing ones to explore different aspects of the data.

## Future Enhancements

Potential features to add:

- Compare multiple units side-by-side
- Visualize stat distributions with charts
- Support for multiple catalogue files
- Army list builder
- Export to different formats
- Weapon and wargear analysis
