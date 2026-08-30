from __future__ import annotations
import pandas as pd
import streamlit as st
from db import all_listings, upsert_many, delete_all
from manual import parse_manual
from sources import SOURCES

st.set_page_config(page_title="Reichman Apartment Finder", page_icon="🏠", layout="wide")
st.title("🏠 Reichman Apartment Finder")
st.caption("Whole apartments near Reichman • target ₪2,000–3,000 per bedroom • free/local")

with st.sidebar:
    st.header("Search")
    min_rooms = st.slider("Minimum rooms", 3, 6, 4)
    max_ppb = st.slider("Max ₪ / bedroom", 2000, 4000, 3000, 100)
    max_total = st.slider("Max total rent", 6000, 16000, 12000, 500)
    min_sqm = st.slider("Minimum size (sqm)", 0, 160, 80, 10)
    st.divider()
    selected = st.multiselect("Refresh sources", list(SOURCES), default=["Realta", "Janglo", "Zipika"])
    if st.button("🔄 Refresh listings", use_container_width=True):
        total = 0
        progress = st.progress(0)
        for i, name in enumerate(selected):
            try:
                rows = SOURCES[name]()
                total += upsert_many(rows)
                st.success(f"{name}: {len(rows)} found")
            except Exception as e:
                st.warning(f"{name}: {type(e).__name__}: {e}")
            progress.progress((i + 1) / max(1, len(selected)))
        st.toast(f"Saved/updated {total} listings")
    if st.button("🗑️ Clear local database", use_container_width=True):
        delete_all(); st.rerun()

manual_tab, results_tab, links_tab = st.tabs(["➕ Add Facebook / private listing", "⭐ Best apartments", "🔎 Direct search links"])

with manual_tab:
    st.write("Paste a Facebook/WhatsApp/Telegram post or listing URL. This is the fallback for private/login-only places.")
    raw = st.text_area("Paste listing", height=220, placeholder="Paste the whole post here…")
    if st.button("Add listing"):
        rows = parse_manual(raw)
        if rows:
            upsert_many(rows); st.success("Added.")
        else: st.warning("Nothing to add.")
    st.info("Tip: load the included Chrome extension to copy visible Facebook listing text quickly.")

with results_tab:
    rows = all_listings()
    if not rows:
        st.info("No listings yet. Hit Refresh listings in the sidebar.")
    else:
        df = pd.DataFrame(rows)
        for c in ["price", "rooms", "sqm", "price_per_bedroom", "score"]:
            df[c] = pd.to_numeric(df[c], errors="coerce")
        filt = df[
            (df["rooms"].fillna(0) >= min_rooms) &
            (df["price_per_bedroom"].fillna(99999) <= max_ppb) &
            (df["price"].fillna(99999) <= max_total) &
            (df["sqm"].fillna(min_sqm) >= min_sqm)
        ].sort_values(["score", "price_per_bedroom"], ascending=[False, True])
        st.metric("Matching apartments", len(filt))
        show = filt[["score","source","title","price","rooms","bedrooms","price_per_bedroom","sqm","renovated","balcony","mamad","parking","url"]].copy()
        st.dataframe(
            show,
            use_container_width=True,
            hide_index=True,
            column_config={
                "url": st.column_config.LinkColumn("Open"),
                "price": st.column_config.NumberColumn("Rent", format="₪%.0f"),
                "price_per_bedroom": st.column_config.NumberColumn("₪/bed", format="₪%.0f"),
                "score": st.column_config.ProgressColumn("Score", min_value=0, max_value=100),
                "renovated": st.column_config.CheckboxColumn("Renovated"),
                "balcony": st.column_config.CheckboxColumn("Balcony"),
                "mamad": st.column_config.CheckboxColumn("Mamad"),
                "parking": st.column_config.CheckboxColumn("Parking"),
            },
        )
        csv = filt.to_csv(index=False).encode()
        st.download_button("Download results CSV", csv, "apartments.csv", "text/csv")

with links_tab:
    st.write("If a scraper breaks, these get you straight to the live source while the rest of the app keeps working.")
    st.markdown("- [Realta — Herzliya 4 rooms](https://realta.co.il/en/herzliya/4-rooms/)\n- [Realta — Herzliya 5 rooms](https://realta.co.il/en/herzliya/5-rooms/)\n- [Realta — Herzliya 6 rooms](https://realta.co.il/en/herzliya/6-rooms/)\n- [Janglo — Netanya / Herzliya rentals](https://www.janglo.net/real-estate-rentals/nh)\n- [Zipika property search](https://zipika.com/property-search)\n- [Yad2 Herzliya rentals](https://www.yad2.co.il/realestate/rent)")
    st.caption("For direct Yad2 automation, run bash setup_yad2.sh once, then tick Yad2 in Refresh sources. Realta already includes Yad2 as a backup.")
