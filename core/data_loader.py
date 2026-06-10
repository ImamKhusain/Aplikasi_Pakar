"""
Data Loader Module
==================
Loads data from SQLite database and provides helper functions
for symptom categorization.

Note: CSV files are only used for the initial import into SQLite.
All runtime reads come from the database.
"""

import pandas as pd
import streamlit as st
from core.database import get_all_gejala, get_all_penyakit, get_all_rules_cf, get_all_rules_fc


@st.cache_data(ttl=5)
def load_data():
    """Load all data from SQLite and return as DataFrames."""
    gejala_df = get_all_gejala()
    penyakit_df = get_all_penyakit()
    rules_cf_df = get_all_rules_cf()
    rules_fc_df = get_all_rules_fc()
    return gejala_df, penyakit_df, rules_cf_df, rules_fc_df


def clear_cache():
    """Clear the cached data so next load fetches fresh from DB."""
    load_data.clear()


def get_symptom_categories(gejala_df):
    """
    Group symptoms by body system / area for organized display.
    Returns a dict: { category_name: [(id_gejala, nama_gejala), ...] }

    Categories are based on the symptom descriptions for baby diseases.
    """
    categories = {
        "Gejala Pernapasan": [],
        "Gejala Demam & Umum": [],
        "Gejala Pencernaan": [],
        "Gejala Kulit & Lainnya": [],
    }

    for _, row in gejala_df.iterrows():
        gid = row['id_gejala']
        name = row['nama_gejala']
        name_lower = name.lower()

        if any(k in name_lower for k in [
            'batuk', 'napas', 'pilek', 'sesak', 'dinding dada',
            'mengi', 'stridor', 'hidung', 'tenggorokan', 'menelan',
            'bibir membiru'
        ]):
            categories["Gejala Pernapasan"].append((gid, name))
        elif any(k in name_lower for k in [
            'demam', 'kejang', 'letargis', 'sadar', 'mengantuk',
            'kaku kuduk', 'berkeringat', 'rewel'
        ]):
            categories["Gejala Demam & Umum"].append((gid, name))
        elif any(k in name_lower for k in [
            'diare', 'bab', 'muntah', 'perut', 'minum', 'haus',
            'cekung', 'urin', 'dehidrasi', 'nafsu makan',
            'berat badan'
        ]):
            categories["Gejala Pencernaan"].append((gid, name))
        else:
            categories["Gejala Kulit & Lainnya"].append((gid, name))

    return categories
