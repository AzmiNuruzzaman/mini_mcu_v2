# utils/cache_utils.py
import os
import shutil
import streamlit as st

def clear_pycache():
    """Remove all __pycache__ folders recursively."""
    for root, dirs, files in os.walk("."):
        for d in dirs:
            if d == "__pycache__":
                full_path = os.path.join(root, d)
                shutil.rmtree(full_path)
                print(f"Removed {full_path}")

def clear_streamlit_cache():
    """Clear Streamlit cache data and resources."""
    if hasattr(st, "cache_data"):
        st.cache_data.clear()
    if hasattr(st, "cache_resource"):
        st.cache_resource.clear()
    print("✅ Streamlit cache cleared.")

def clear_all():
    """Clear both __pycache__ folders and Streamlit cache."""
    clear_pycache()
    clear_streamlit_cache()
