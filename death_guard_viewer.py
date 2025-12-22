"""
Death Guard Catalogue Viewer
A Streamlit application to explore and visualize Warhammer 40k Death Guard army data
"""

import streamlit as st
import xml.etree.ElementTree as ET
import pandas as pd
from pathlib import Path
from typing import List, Dict, Optional

# Set page config
st.set_page_config(
    page_title="Death Guard Catalogue Viewer",
    page_icon="☠️",
    layout="wide",
    initial_sidebar_state="expanded"
)

@st.cache_data
def parse_catalogue(file_path: str) -> tuple:
    """Parse the Death Guard catalogue XML file"""
    tree = ET.parse(file_path)
    root = tree.getroot()

    # Get namespace
    ns = {'cat': 'http://www.battlescribe.net/schema/catalogueSchema'}

    # Get catalogue metadata
    catalogue_info = {
        'name': root.get('name'),
        'revision': root.get('revision'),
        'id': root.get('id'),
        'battleScribeVersion': root.get('battleScribeVersion')
    }

    return root, ns, catalogue_info

@st.cache_data
def extract_entry_links(_root, _ns) -> pd.DataFrame:
    """Extract all entry links (units) from the catalogue"""
    entries = []

    for entry in _root.findall('.//cat:entryLink', _ns):
        entry_data = {
            'id': entry.get('id'),
            'name': entry.get('name'),
            'type': entry.get('type'),
            'targetId': entry.get('targetId'),
            'hidden': entry.get('hidden', 'false'),
            'import': entry.get('import', 'false')
        }
        entries.append(entry_data)

    return pd.DataFrame(entries)

@st.cache_data
def extract_shared_selections(_root, _ns) -> pd.DataFrame:
    """Extract shared selection entries (actual unit definitions)"""
    selections = []

    for selection in _root.findall('.//cat:sharedSelectionEntries/cat:selectionEntry', _ns):
        selection_data = {
            'id': selection.get('id'),
            'name': selection.get('name'),
            'type': selection.get('type'),
            'publicationId': selection.get('publicationId', ''),
            'page': selection.get('page', ''),
            'hidden': selection.get('hidden', 'false')
        }

        # Get costs
        costs = selection.findall('.//cat:cost', _ns)
        for cost in costs:
            cost_name = cost.get('name')
            cost_value = cost.get('value', '0.0')
            selection_data[f'cost_{cost_name}'] = cost_value

        # Get categories
        categories = selection.findall('.//cat:categoryLink', _ns)
        cat_list = [cat.get('name') for cat in categories if cat.get('name')]
        selection_data['categories'] = ', '.join(cat_list)

        selections.append(selection_data)

    return pd.DataFrame(selections)

@st.cache_data
def extract_profiles(_root, _ns) -> pd.DataFrame:
    """Extract unit profiles (stats)"""
    profiles = []

    for profile in _root.findall('.//cat:profile', _ns):
        profile_data = {
            'id': profile.get('id'),
            'name': profile.get('name'),
            'type': profile.get('typeName'),
            'publicationId': profile.get('publicationId', ''),
            'page': profile.get('page', '')
        }

        # Get characteristics (stats)
        characteristics = profile.findall('.//cat:characteristic', _ns)
        for char in characteristics:
            char_name = char.get('name')
            char_value = char.text if char.text else ''
            profile_data[char_name] = char_value

        profiles.append(profile_data)

    return pd.DataFrame(profiles)

@st.cache_data
def extract_rules(_root, _ns) -> pd.DataFrame:
    """Extract special rules and abilities"""
    rules = []

    for rule in _root.findall('.//cat:rule', _ns):
        rule_data = {
            'id': rule.get('id'),
            'name': rule.get('name'),
            'publicationId': rule.get('publicationId', ''),
            'page': rule.get('page', ''),
            'hidden': rule.get('hidden', 'false')
        }

        # Get description
        description = rule.find('cat:description', _ns)
        if description is not None and description.text:
            rule_data['description'] = description.text
        else:
            rule_data['description'] = ''

        rules.append(rule_data)

    return pd.DataFrame(rules)

@st.cache_data
def extract_catalogue_links(_root, _ns) -> pd.DataFrame:
    """Extract linked catalogues"""
    links = []

    for link in _root.findall('.//cat:catalogueLink', _ns):
        link_data = {
            'id': link.get('id'),
            'name': link.get('name'),
            'targetId': link.get('targetId'),
            'type': link.get('type'),
            'importRootEntries': link.get('importRootEntries', 'false')
        }
        links.append(link_data)

    return pd.DataFrame(links)

def main():
    st.title("☠️ Death Guard Catalogue Viewer")
    st.markdown("Explore the Warhammer 40k Death Guard army catalogue data")

    # File path
    cat_file = Path(__file__).parent / "Chaos - Death Guard.cat"

    if not cat_file.exists():
        st.error(f"Catalogue file not found: {cat_file}")
        return

    # Parse catalogue
    try:
        root, ns, catalogue_info = parse_catalogue(str(cat_file))

        # Sidebar - Catalogue Info
        with st.sidebar:
            st.header("📋 Catalogue Information")
            st.write(f"**Name:** {catalogue_info['name']}")
            st.write(f"**Revision:** {catalogue_info['revision']}")
            st.write(f"**BattleScribe Version:** {catalogue_info['battleScribeVersion']}")
            st.write(f"**ID:** {catalogue_info['id']}")

            st.divider()

            # View selector
            st.header("🔍 Select View")
            view = st.radio(
                "Choose what to display:",
                [
                    "Overview",
                    "Units (Entry Links)",
                    "Unit Definitions",
                    "Unit Profiles & Stats",
                    "Rules & Abilities",
                    "Linked Catalogues",
                    "Search"
                ]
            )

        # Main content area
        if view == "Overview":
            st.header("📊 Catalogue Overview")

            col1, col2, col3 = st.columns(3)

            entry_links = extract_entry_links(root, ns)
            shared_selections = extract_shared_selections(root, ns)
            profiles = extract_profiles(root, ns)
            rules = extract_rules(root, ns)

            with col1:
                st.metric("Total Entry Links", len(entry_links))
                st.metric("Shared Selections", len(shared_selections))

            with col2:
                st.metric("Unit Profiles", len(profiles))
                st.metric("Rules & Abilities", len(rules))

            with col3:
                visible_units = entry_links[entry_links['hidden'] == 'false']
                st.metric("Visible Units", len(visible_units))
                legends = entry_links[entry_links['name'].str.contains('Legends', na=False)]
                st.metric("Legends Units", len(legends))

            st.divider()

            # Show recent units
            st.subheader("🎯 Available Units (Sample)")
            st.dataframe(
                entry_links[entry_links['hidden'] == 'false'][['name', 'type']].head(20),
                use_container_width=True,
                hide_index=True
            )

        elif view == "Units (Entry Links)":
            st.header("🎯 Unit Entry Links")
            st.markdown("These are the units available in the Death Guard army")

            entry_links = extract_entry_links(root, ns)

            # Filters
            col1, col2 = st.columns(2)
            with col1:
                show_hidden = st.checkbox("Show hidden units", value=False)
            with col2:
                search_term = st.text_input("Search units by name", "")

            # Apply filters
            filtered_df = entry_links.copy()
            if not show_hidden:
                filtered_df = filtered_df[filtered_df['hidden'] == 'false']
            if search_term:
                filtered_df = filtered_df[filtered_df['name'].str.contains(search_term, case=False, na=False)]

            st.write(f"Showing {len(filtered_df)} units")

            st.dataframe(
                filtered_df[['name', 'type', 'hidden', 'id']],
                use_container_width=True,
                hide_index=True,
                height=600
            )

        elif view == "Unit Definitions":
            st.header("📖 Unit Definitions (Shared Selections)")
            st.markdown("Detailed unit definitions with costs and categories")

            shared_selections = extract_shared_selections(root, ns)

            if len(shared_selections) > 0:
                # Search
                search_term = st.text_input("Search unit definitions", "")

                filtered_df = shared_selections.copy()
                if search_term:
                    filtered_df = filtered_df[filtered_df['name'].str.contains(search_term, case=False, na=False)]

                st.write(f"Showing {len(filtered_df)} unit definitions")

                # Select columns to display
                all_columns = filtered_df.columns.tolist()
                default_columns = ['name', 'type', 'categories']
                cost_columns = [col for col in all_columns if col.startswith('cost_')]
                default_columns.extend(cost_columns[:3])  # Add first 3 cost columns

                display_columns = st.multiselect(
                    "Select columns to display",
                    options=all_columns,
                    default=[col for col in default_columns if col in all_columns]
                )

                if display_columns:
                    st.dataframe(
                        filtered_df[display_columns],
                        use_container_width=True,
                        hide_index=True,
                        height=600
                    )
            else:
                st.info("No shared selection entries found in this catalogue")

        elif view == "Unit Profiles & Stats":
            st.header("📊 Unit Profiles & Stats")
            st.markdown("Combat statistics and characteristics for units")

            profiles = extract_profiles(root, ns)

            if len(profiles) > 0:
                # Filter by profile type
                profile_types = profiles['type'].unique().tolist()
                selected_type = st.selectbox("Filter by profile type", ['All'] + profile_types)

                search_term = st.text_input("Search profiles", "")

                filtered_df = profiles.copy()
                if selected_type != 'All':
                    filtered_df = filtered_df[filtered_df['type'] == selected_type]
                if search_term:
                    filtered_df = filtered_df[filtered_df['name'].str.contains(search_term, case=False, na=False)]

                st.write(f"Showing {len(filtered_df)} profiles")

                # Show profile type distribution
                with st.expander("📈 Profile Type Distribution"):
                    type_counts = profiles['type'].value_counts()
                    st.bar_chart(type_counts)

                st.dataframe(
                    filtered_df,
                    use_container_width=True,
                    hide_index=True,
                    height=600
                )

                # Export option
                if st.button("Export to CSV"):
                    csv = filtered_df.to_csv(index=False)
                    st.download_button(
                        label="Download CSV",
                        data=csv,
                        file_name="death_guard_profiles.csv",
                        mime="text/csv"
                    )
            else:
                st.info("No profiles found in this catalogue")

        elif view == "Rules & Abilities":
            st.header("⚔️ Rules & Abilities")
            st.markdown("Special rules, abilities, and army mechanics")

            rules = extract_rules(root, ns)

            if len(rules) > 0:
                search_term = st.text_input("Search rules", "")

                filtered_df = rules.copy()
                if search_term:
                    mask = (
                        filtered_df['name'].str.contains(search_term, case=False, na=False) |
                        filtered_df['description'].str.contains(search_term, case=False, na=False)
                    )
                    filtered_df = filtered_df[mask]

                st.write(f"Showing {len(filtered_df)} rules")

                # Display rules with expandable descriptions
                for _, rule in filtered_df.iterrows():
                    with st.expander(f"**{rule['name']}** {f'(Page {rule['page']})' if rule.get('page') else ''}"):
                        if rule.get('description'):
                            st.markdown(rule['description'])
                        else:
                            st.write("_No description available_")
                        st.caption(f"ID: {rule['id']}")
            else:
                st.info("No rules found in this catalogue")

        elif view == "Linked Catalogues":
            st.header("🔗 Linked Catalogues")
            st.markdown("External catalogues referenced by Death Guard")

            catalogue_links = extract_catalogue_links(root, ns)

            if len(catalogue_links) > 0:
                st.dataframe(
                    catalogue_links,
                    use_container_width=True,
                    hide_index=True
                )
            else:
                st.info("No catalogue links found")

        elif view == "Search":
            st.header("🔎 Global Search")
            st.markdown("Search across all data types")

            search_term = st.text_input("Enter search term", "")

            if search_term:
                st.subheader("Search Results")

                # Search in entry links
                entry_links = extract_entry_links(root, ns)
                matching_entries = entry_links[entry_links['name'].str.contains(search_term, case=False, na=False)]
                if len(matching_entries) > 0:
                    st.write(f"**Found {len(matching_entries)} matching units:**")
                    st.dataframe(matching_entries[['name', 'type']], use_container_width=True, hide_index=True)

                # Search in rules
                rules = extract_rules(root, ns)
                matching_rules = rules[
                    rules['name'].str.contains(search_term, case=False, na=False) |
                    rules['description'].str.contains(search_term, case=False, na=False)
                ]
                if len(matching_rules) > 0:
                    st.write(f"**Found {len(matching_rules)} matching rules:**")
                    for _, rule in matching_rules.iterrows():
                        with st.expander(rule['name']):
                            st.markdown(rule.get('description', '_No description_'))

                # Search in profiles
                profiles = extract_profiles(root, ns)
                matching_profiles = profiles[profiles['name'].str.contains(search_term, case=False, na=False)]
                if len(matching_profiles) > 0:
                    st.write(f"**Found {len(matching_profiles)} matching profiles:**")
                    st.dataframe(matching_profiles[['name', 'type']], use_container_width=True, hide_index=True)
            else:
                st.info("Enter a search term to find units, rules, and profiles")

    except Exception as e:
        st.error(f"Error parsing catalogue: {str(e)}")
        st.exception(e)

if __name__ == "__main__":
    main()
