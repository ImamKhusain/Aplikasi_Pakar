"""
Sistem Pakar Diagnosa Penyakit Pada Bayi dengan Certainty Factor
================================================================
Metode: Forward Chaining & Certainty Factor

Main entry point.
Run with: streamlit run app.py
"""

import streamlit as st
import pandas as pd
import re

# --- Page Configuration (must be the first Streamlit command) ---
st.set_page_config(
    page_title="Sistem Pakar — Diagnosa Penyakit Bayi",
    layout="wide",
    initial_sidebar_state="expanded",
)

# --- Initialize Database (creates tables + imports CSV on first run) ---
from core.database import (
    init_database, authenticate,
    get_all_users, add_user, update_user, delete_user,
    get_all_penyakit, add_penyakit, update_penyakit, delete_penyakit, get_next_penyakit_id,
    get_all_gejala, add_gejala, update_gejala, delete_gejala, get_next_gejala_id,
    get_all_rules_cf, add_rule_cf, update_rule_cf, delete_rule_cf,
    get_next_rule_cf_id, check_duplicate_rule_cf,
    get_all_rules_fc, add_rule_fc, update_rule_fc, delete_rule_fc, get_next_rule_fc_id,
    get_related_rules_count,
)
from core.data_loader import load_data, get_symptom_categories, clear_cache
from core.engine import diagnose, get_related_symptoms
from login import show_login_page

init_database()

# --- Session State Init ---
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "user_info" not in st.session_state:
    st.session_state.user_info = None
if "remember_me" not in st.session_state:
    st.session_state.remember_me = False


# =============================================
# LOGIN PAGE
# =============================================
if not st.session_state.logged_in:
    show_login_page(authenticate)
    st.stop()


# =============================================
# LOGGED IN — Main Application
# =============================================
user_info = st.session_state.user_info
user_role = user_info['role']

# --- Load Data from SQLite ---
gejala_df, penyakit_df, rules_cf_df, rules_fc_df = load_data()

# --- Mapping skala keyakinan user untuk Certainty Factor ---
# Nilai ini dipakai sebagai CF_user pada rumus: CF_gejala = CF_pakar × CF_user
LIKERT_CF_USER = {
    "Sangat Lemah": 0.2,
    "Lemah": 0.4,
    "Cukup Kuat": 0.6,
    "Kuat": 0.8,
    "Sangat Kuat": 1.0,
}


# =============================================
# SIDEBAR — Navigation
# =============================================
st.sidebar.title("Sistem Pakar Bayi")
st.sidebar.markdown("---")

# User info
st.sidebar.success(
    f"**{user_info['nama_lengkap']}**\n\n"
    f"Role: **{user_info['role'].upper()}**"
)

# Logout
if st.sidebar.button("Logout", use_container_width=True):
    st.session_state.logged_in = False
    st.session_state.user_info = None
    st.session_state.remember_me = False
    st.rerun()

st.sidebar.markdown("---")

# Menu options based on role
menu_options = [
    "Beranda",
    "Diagnosa",
    "Data Penyakit",
    "Data Gejala",
    "Data Rules CF",
    "Data Rules Forward Chaining",
    "Tentang Metode",
]

if user_role == "admin":
    menu_options.append("Admin Panel")

menu = st.sidebar.radio("Navigasi", options=menu_options)

st.sidebar.markdown("---")
st.sidebar.info(
    f"**Statistik Data**\n\n"
    f"- Gejala: **{len(gejala_df)}**\n"
    f"- Penyakit: **{len(penyakit_df)}**\n"
    f"- Rules CF: **{len(rules_cf_df)}**\n"
    f"- Rules FC: **{len(rules_fc_df)}**"
)


# =============================================
# PAGE: Beranda
# =============================================
if menu == "Beranda":
    st.title("Sistem Pakar Diagnosa Penyakit Pada Bayi")
    st.subheader("Metode: Forward Chaining & Certainty Factor")

    st.markdown("""
    Selamat datang di **Sistem Pakar Diagnosa Penyakit Pada Bayi**. 
    Aplikasi ini membantu mendiagnosa kemungkinan penyakit pada bayi berdasarkan 
    gejala-gejala yang diamati, menggunakan metode **Forward Chaining** dan 
    **Certainty Factor (CF)**.
    """)

    st.markdown("---")

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Gejala", len(gejala_df))
    with col2:
        st.metric("Jenis Penyakit", len(penyakit_df))
    with col3:
        st.metric("Rules CF", len(rules_cf_df))
    with col4:
        st.metric("Rules FC", len(rules_fc_df))

    st.markdown("---")

    st.subheader("Cara Penggunaan")
    st.markdown("""
    1. Buka menu **Diagnosa** di sidebar
    2. Pilih gejala-gejala yang dialami bayi
    3. Klik tombol **Mulai Diagnosa**
    4. Sistem akan menjalankan **Forward Chaining** untuk menemukan penyakit yang cocok
    5. Kemudian menghitung **Certainty Factor** untuk mengukur tingkat kepastian
    6. Lihat detail proses FC dan perhitungan CF untuk transparansi hasil
    """)

    st.subheader("Alur Kerja Sistem")
    st.markdown("""
    ```
    Gejala Dipilih User
         │
         ▼
    ┌─────────────────────────┐
    │  FORWARD CHAINING       │  ← Evaluasi rules forward chaining
    │  (Evaluasi kondisi      │     (AND/OR conditions)
    │   IF-THEN)              │
    └─────────┬───────────────┘
              │ Penyakit yang ter-trigger
              ▼
    ┌─────────────────────────┐
    │  CERTAINTY FACTOR       │  ← Hitung dari rules CF
    │  (Hitung tingkat        │     (bobot CF per gejala)
    │   kepastian)            │
    └─────────┬───────────────┘
              │
              ▼
         Hasil Diagnosa
    (Diurutkan berdasarkan CF)
    ```
    """)

    st.subheader("Daftar Penyakit yang Dapat Didiagnosa")
    for _, row in penyakit_df.iterrows():
        st.markdown(f"- **{row['id_penyakit']}** — {row['nama_penyakit']}")


# =============================================
# PAGE: Diagnosa
# =============================================
elif menu == "Diagnosa":
    st.title("Diagnosa Penyakit Bayi")
    st.markdown("Pilih gejala-gejala yang dialami bayi, tentukan tingkat keyakinan, lalu klik **Mulai Diagnosa**.")
    st.markdown("---")

    # --- Symptom Selection ---
    categories = get_symptom_categories(gejala_df)
    selected_gejala = []
    gejala_cf_user = {}
    gejala_lookup_ui = dict(zip(gejala_df["id_gejala"], gejala_df["nama_gejala"]))

    for cat_name, symptoms in categories.items():
        if not symptoms:
            continue
        with st.expander(f"{cat_name}  ({len(symptoms)} gejala)", expanded=True):
            options = [f"[{gid}] {name}" for gid, name in symptoms]
            selected = st.multiselect(
                label=f"Pilih gejala — {cat_name}",
                options=options,
                placeholder="Klik untuk memilih gejala...",
                label_visibility="collapsed",
                key=f"ms_{cat_name}",
            )
            for sel in selected:
                gid = sel.split("]")[0].replace("[", "").strip()
                selected_gejala.append(gid)

    # Hilangkan duplikasi gejala jika ada gejala yang muncul di lebih dari satu kategori
    selected_gejala = list(dict.fromkeys(selected_gejala))

    st.markdown("---")

    if selected_gejala:
        st.success(f"**{len(selected_gejala)}** gejala dipilih")

        # === INPUT CF USER BERDASARKAN SKALA LIKERT ===
        st.markdown("---")
        st.subheader("Tingkat Keyakinan User")
        st.markdown(
            "Tentukan seberapa yakin Anda bahwa setiap gejala benar-benar dialami bayi. "
            "Nilai ini akan dipakai sebagai **CF User** pada perhitungan Certainty Factor."
        )

        likert_df = pd.DataFrame([
            {"Interpretasi User": label, "CF User": nilai}
            for label, nilai in LIKERT_CF_USER.items()
        ])
        st.dataframe(likert_df, use_container_width=True, hide_index=True)

        with st.expander("Isi tingkat keyakinan untuk setiap gejala", expanded=True):
            for gid in selected_gejala:
                nama_gejala = gejala_lookup_ui.get(gid, gid)
                pilihan_keyakinan = st.select_slider(
                    label=f"[{gid}] {nama_gejala}",
                    options=list(LIKERT_CF_USER.keys()),
                    value="Sangat Kuat",
                    key=f"cf_user_{gid}",
                )
                gejala_cf_user[gid] = LIKERT_CF_USER[pilihan_keyakinan]

        st.caption("Rumus yang digunakan: CF gejala = CF pakar × CF user.")

        # === GUIDED DIAGNOSIS: Show related symptom suggestions ===
        suggestions = get_related_symptoms(
            selected_gejala, rules_fc_df, penyakit_df, gejala_df
        )

        if suggestions:
            st.markdown("---")
            st.subheader("Saran Gejala Terkait")
            st.markdown(
                "Berdasarkan gejala yang Anda pilih, berikut gejala lain yang mungkin "
                "perlu diperiksa untuk memperkuat diagnosa:"
            )

            for sg in suggestions:
                with st.expander(
                    f"Kemungkinan: **{sg['nama_penyakit']}** ({sg['id_penyakit']}) "
                    f"— {sg['matched_count']}/{sg['total_needed']} gejala cocok "
                    f"({sg['completion_pct']:.0f}%)",
                    expanded=(sg['completion_pct'] >= 30),
                ):
                    # Progress bar for rule completion
                    st.progress(
                        sg['completion_pct'] / 100,
                        text=f"Kelengkapan gejala: {sg['matched_count']}/{sg['total_needed']} ({sg['completion_pct']:.0f}%)",
                    )

                    st.markdown("**Gejala yang disarankan untuk diperiksa:**")
                    for sym in sg['suggested_symptoms']:
                        rule_info = ", ".join(sym['from_rules'])
                        st.markdown(
                            f"- **{sym['id_gejala']}** — {sym['nama_gejala']} "
                            f"_(dari rule: {rule_info})_"
                        )

            st.markdown("---")
    else:
        st.info("Belum ada gejala yang dipilih. Silakan pilih gejala di atas.")

    # --- Diagnose Button ---
    diagnose_clicked = st.button(
        "Mulai Diagnosa", type="primary", use_container_width=True,
    )

    if diagnose_clicked:
        if not selected_gejala:
            st.warning("Silakan pilih minimal satu gejala sebelum melakukan diagnosa!")
        else:
            with st.spinner("Menjalankan proses diagnosa..."):
                hasil = diagnose(
                    selected_gejala, rules_cf_df, rules_fc_df,
                    penyakit_df, gejala_df,
                    gejala_cf_user=gejala_cf_user,
                )

            if hasil is None:
                st.error(
                    "**Tidak Ditemukan Kecocokan**\n\n"
                    "Tidak ditemukan penyakit yang cocok dengan kombinasi gejala tersebut "
                    "berdasarkan rules forward chaining. "
                    "Coba pilih gejala yang berbeda atau tambahkan gejala lainnya."
                )
            else:
                st.markdown("---")
                st.subheader("Hasil Diagnosa")

                utama = hasil[0]
                st.markdown(f"### Diagnosis Utama: **{utama['nama_penyakit']}**")

                col_a, col_b = st.columns(2)
                with col_a:
                    st.metric("Kode Penyakit", utama['id_penyakit'])
                with col_b:
                    st.metric("Tingkat Kepastian (CF)", f"{utama['persentase']:.2f}%")

                st.progress(utama['cf_akhir'])

                with st.expander("Detail Forward Chaining", expanded=False):
                    st.markdown(f"**Penyakit:** {utama['nama_penyakit']} ({utama['id_penyakit']})")
                    st.markdown("**Rules yang ter-trigger:**")
                    for fc in utama['fc_triggered_rules']:
                        st.markdown(f"- **{fc['id_rule']}**: `IF {fc['kondisi_if']} THEN {utama['id_penyakit']}`")
                        st.markdown(f"  → Kondisi terpenuhi: {fc['kondisi_readable']}")

                with st.expander("Detail Gejala & Bobot CF", expanded=False):
                    for sym in utama['matched_symptoms']:
                        st.markdown(
                            f"- **{sym['id_gejala']}** — {sym['nama_gejala']}  \n"
                            f"  CF Pakar: `{sym['bobot_cf']}` | "
                            f"CF User: `{sym.get('cf_user', 1.0)}` | "
                            f"CF Gejala: `{sym.get('cf_gejala', sym['bobot_cf']):.4f}`"
                        )

                with st.expander("Detail Perhitungan CF", expanded=False):
                    st.markdown(f"**Penyakit:** {utama['nama_penyakit']} ({utama['id_penyakit']})")
                    st.markdown("**Langkah-langkah perhitungan:**")
                    for step in utama['calculation_steps']:
                        st.markdown(f"- {step}")
                    st.markdown(f"**CF Akhir = {utama['cf_akhir']:.4f} ({utama['persentase']:.2f}%)**")

                if len(hasil) > 1:
                    st.markdown("---")
                    st.subheader("Kemungkinan Penyakit Lainnya")

                    for hd in hasil[1:]:
                        with st.container():
                            col1, col2, col3 = st.columns([3, 1, 1])
                            with col1:
                                st.markdown(f"**{hd['nama_penyakit']}**")
                            with col2:
                                st.markdown(f"`{hd['id_penyakit']}`")
                            with col3:
                                st.markdown(f"**{hd['persentase']:.2f}%**")

                            st.progress(hd['cf_akhir'])

                            with st.expander(f"Detail — {hd['nama_penyakit']}", expanded=False):
                                st.markdown("**Forward Chaining — Rules yang ter-trigger:**")
                                for fc in hd['fc_triggered_rules']:
                                    st.markdown(f"- **{fc['id_rule']}**: `IF {fc['kondisi_if']} THEN {hd['id_penyakit']}`")
                                st.markdown("---")
                                st.markdown("**Gejala yang cocok (CF):**")
                                for sym in hd['matched_symptoms']:
                                    st.markdown(
                                        f"- **{sym['id_gejala']}** — {sym['nama_gejala']}  \n"
                                        f"  CF Pakar: `{sym['bobot_cf']}` | "
                                        f"CF User: `{sym.get('cf_user', 1.0)}` | "
                                        f"CF Gejala: `{sym.get('cf_gejala', sym['bobot_cf']):.4f}`"
                                    )
                                st.markdown("**Perhitungan CF:**")
                                for step in hd['calculation_steps']:
                                    st.markdown(f"- {step}")
                                st.markdown(
                                    f"**CF Akhir = {hd['cf_akhir']:.4f} ({hd['persentase']:.2f}%)**"
                                )

                st.markdown("---")
                st.subheader("Ringkasan Semua Hasil")
                summary_data = []
                for i, h in enumerate(hasil, 1):
                    summary_data.append({
                        "No": i,
                        "Kode": h['id_penyakit'],
                        "Nama Penyakit": h['nama_penyakit'],
                        "Rules FC": len(h['fc_triggered_rules']),
                        "Gejala CF": len(h['matched_symptoms']),
                        "CF Akhir": f"{h['cf_akhir']:.4f}",
                        "Persentase": f"{h['persentase']:.2f}%",
                    })
                st.dataframe(pd.DataFrame(summary_data), use_container_width=True, hide_index=True)#..


# =============================================
# PAGE: Data Penyakit
# =============================================
elif menu == "Data Penyakit":
    st.title("Data Penyakit")
    st.markdown("Daftar penyakit yang terdapat dalam basis pengetahuan sistem pakar.")
    st.markdown("---")

    st.dataframe(penyakit_df, use_container_width=True, hide_index=True)
    st.markdown(f"**Total Penyakit:** {len(penyakit_df)}")

    st.markdown("---")
    st.subheader("Jumlah Rules per Penyakit")

    cf_count = rules_cf_df.groupby('id_penyakit').size().reset_index(name='rules_cf')
    fc_count = rules_fc_df.groupby('id_penyakit').size().reset_index(name='rules_fc')
    merged = penyakit_df.merge(cf_count, on='id_penyakit', how='left')
    merged = merged.merge(fc_count, on='id_penyakit', how='left').fillna(0)
    merged['rules_cf'] = merged['rules_cf'].astype(int)
    merged['rules_fc'] = merged['rules_fc'].astype(int)
    merged = merged[['id_penyakit', 'nama_penyakit', 'rules_cf', 'rules_fc']]
    merged.columns = ['Kode', 'Nama Penyakit', 'Rules CF', 'Rules FC']
    st.dataframe(merged, use_container_width=True, hide_index=True)
    st.bar_chart(merged.set_index('Nama Penyakit')[['Rules CF', 'Rules FC']])


# =============================================
# PAGE: Data Gejala
# =============================================
elif menu == "Data Gejala":
    st.title("Data Gejala")
    st.markdown("Daftar gejala penyakit bayi dalam basis pengetahuan.")
    st.markdown("---")

    st.dataframe(gejala_df, use_container_width=True, hide_index=True)
    st.markdown(f"**Total Gejala:** {len(gejala_df)}")

    st.markdown("---")
    st.subheader("Relasi Gejala — Penyakit (CF)")

    search_gejala = st.selectbox(
        "Pilih gejala untuk melihat penyakit terkait:",
        options=[f"[{row['id_gejala']}] {row['nama_gejala']}" for _, row in gejala_df.iterrows()],
        index=None, placeholder="Cari gejala...",
    )
    if search_gejala:
        gid = search_gejala.split("]")[0].replace("[", "").strip()
        related = rules_cf_df[rules_cf_df['id_gejala'] == gid]
        if related.empty:
            st.info("Gejala ini tidak terkait dengan penyakit manapun dalam rules CF.")
        else:
            display = related.merge(penyakit_df, on='id_penyakit')
            display = display[['id_rule', 'id_penyakit', 'nama_penyakit', 'bobot_cf']]
            display.columns = ['Rule', 'Kode Penyakit', 'Nama Penyakit', 'Bobot CF']
            st.dataframe(display, use_container_width=True, hide_index=True)


# =============================================
# PAGE: Data Rules CF
# =============================================
elif menu == "Data Rules CF":
    st.title("Data Rules — Certainty Factor")
    st.markdown("Basis aturan (rules) yang menghubungkan gejala dengan penyakit beserta bobot CF-nya.")
    st.markdown("---")

    display_rules = rules_cf_df.merge(penyakit_df, on='id_penyakit').merge(gejala_df, on='id_gejala')
    display_rules = display_rules[['id_rule', 'id_penyakit', 'nama_penyakit', 'id_gejala', 'nama_gejala', 'bobot_cf']]
    display_rules.columns = ['Rule', 'Kode Penyakit', 'Nama Penyakit', 'Kode Gejala', 'Nama Gejala', 'Bobot CF']

    filter_p = st.selectbox(
        "Filter berdasarkan penyakit:",
        options=["Semua"] + [f"[{r['id_penyakit']}] {r['nama_penyakit']}" for _, r in penyakit_df.iterrows()],
        key="filter_cf",
    )
    if filter_p != "Semua":
        pid = filter_p.split("]")[0].replace("[", "").strip()
        display_rules = display_rules[display_rules['Kode Penyakit'] == pid]

    st.dataframe(display_rules, use_container_width=True, hide_index=True)
    st.markdown(f"**Total Rules ditampilkan:** {len(display_rules)}")

    st.markdown("---")
    st.subheader("Distribusi Bobot CF")
    cf_dist = rules_cf_df['bobot_cf'].value_counts().sort_index().reset_index()
    cf_dist.columns = ['Bobot CF', 'Jumlah Rules']
    st.bar_chart(cf_dist.set_index('Bobot CF'))


# =============================================
# PAGE: Data Rules Forward Chaining
# =============================================
elif menu == "Data Rules Forward Chaining":
    st.title("Data Rules — Forward Chaining")
    st.markdown("Basis aturan forward chaining yang mendefinisikan kondisi logis (IF-THEN).")
    st.markdown("---")

    gejala_lookup = dict(zip(gejala_df['id_gejala'], gejala_df['nama_gejala']))
    display_data = []
    for _, rule in rules_fc_df.iterrows():
        condition = rule['kondisi_if']
        condition_readable = condition
        for sid in re.findall(r'G\d+', condition):
            sname = gejala_lookup.get(sid, sid)
            condition_readable = condition_readable.replace(sid, f"{sid} ({sname})")
        pname = penyakit_df[penyakit_df['id_penyakit'] == rule['id_penyakit']]['nama_penyakit'].values
        pname = pname[0] if len(pname) > 0 else rule['id_penyakit']
        display_data.append({
            'Rule': rule['id_rule'], 'Kondisi IF': rule['kondisi_if'],
            'Kondisi (Readable)': condition_readable,
            'Kode Penyakit': rule['id_penyakit'], 'Nama Penyakit (THEN)': pname,
        })
    display_fc_df = pd.DataFrame(display_data)

    filter_fc = st.selectbox(
        "Filter berdasarkan penyakit:",
        options=["Semua"] + [f"[{r['id_penyakit']}] {r['nama_penyakit']}" for _, r in penyakit_df.iterrows()],
        key="filter_fc",
    )
    if filter_fc != "Semua":
        pid = filter_fc.split("]")[0].replace("[", "").strip()
        display_fc_df = display_fc_df[display_fc_df['Kode Penyakit'] == pid]

    st.dataframe(display_fc_df, use_container_width=True, hide_index=True)
    st.markdown(f"**Total Rules ditampilkan:** {len(display_fc_df)}")

    st.subheader("Rules dalam Format IF-THEN")
    for _, row in display_fc_df.iterrows():
        st.code(
            f"[{row['Rule']}] IF {row['Kondisi (Readable)']} "
            f"THEN Penyakit = {row['Nama Penyakit (THEN)']} ({row['Kode Penyakit']})",
            language=None,
        )


# =============================================
# PAGE: Tentang Metode
# =============================================
elif menu == "Tentang Metode":
    st.title("Tentang Metode yang Digunakan")
    st.markdown("---")

    st.subheader("Forward Chaining")
    st.markdown("""
    **Forward Chaining** adalah metode penalaran maju (*data-driven*) dalam sistem pakar.
    Proses dimulai dari **fakta-fakta** (gejala yang dipilih pengguna) kemudian dicocokkan
    dengan **aturan (rules)** dalam basis pengetahuan untuk mencapai **kesimpulan** berupa
    diagnosis penyakit.
    
    Dalam sistem ini, rules forward chaining menggunakan **kondisi logis** (AND/OR):
    - **AND**: Semua gejala dalam kondisi harus dipilih agar rule ter-trigger
    - **OR**: Minimal satu gejala dalam kondisi harus dipilih agar rule ter-trigger
    
    **Alur Forward Chaining:**
    1. User memilih gejala yang dialami bayi
    2. Sistem mengevaluasi setiap rule forward chaining
    3. Rule yang kondisinya terpenuhi akan men-trigger penyakit terkait
    4. Penyakit yang ter-trigger dilanjutkan ke tahap perhitungan CF
    """)

    st.markdown("---")

    st.subheader("Certainty Factor (CF)")
    st.markdown("""
    **Certainty Factor** adalah metode untuk mengukur tingkat keyakinan/kepastian 
    terhadap suatu hipotesis berdasarkan fakta atau bukti yang ada.
    
    **Nilai CF** berkisar antara **0** (tidak pasti) hingga **1** (pasti).
    
    **Rumus kombinasi CF** ketika terdapat lebih dari satu gejala yang menunjuk 
    pada penyakit yang sama:
    """)

    st.latex(r"CF_{combine}(CF_1, CF_2) = CF_1 + CF_2 \times (1 - CF_1)")

    st.markdown("""
    Pada sistem ini, nilai CF setiap gejala dihitung dari kombinasi antara 
    **CF Pakar** dan **CF User**. CF Pakar berasal dari basis aturan, sedangkan 
    CF User berasal dari tingkat keyakinan pengguna terhadap gejala yang dipilih.
    """)

    st.latex(r"CF_{gejala} = CF_{pakar} \times CF_{user}")

    st.markdown("""
    **Skala CF User:**

    | Interpretasi User | CF User |
    |:---|:---:|
    | Sangat Lemah | 0.2 |
    | Lemah | 0.4 |
    | Cukup Kuat | 0.6 |
    | Kuat | 0.8 |
    | Sangat Kuat | 1.0 |
    """)

    st.markdown("""
    **Contoh perhitungan:**
    - Misal gejala A memiliki CF = 0.8 terhadap penyakit X
    - Misal gejala B memiliki CF = 0.6 terhadap penyakit X
    - CF_combine = 0.8 + 0.6 × (1 - 0.8) = 0.8 + 0.12 = **0.92** (92%)
    
    Semakin banyak gejala yang cocok, semakin tinggi nilai CF (mendekati 1.0 / 100%).
    """)

    st.markdown("---")

    st.subheader("Alur Keseluruhan Sistem")
    st.markdown("""
    ```
    Input: Gejala yang dipilih user
           │
           ▼
    ┌──────────────────────────────┐
    │  TAHAP 1: FORWARD CHAINING  │
    │  Evaluasi rules FC           │
    │  (kondisi AND/OR)            │
    │  → Penyakit mana yang        │
    │    ter-trigger?              │
    └──────────┬───────────────────┘
               │
               ▼
    ┌──────────────────────────────┐
    │  TAHAP 2: CERTAINTY FACTOR  │
    │  Hitung dari rules CF        │
    │  CF gejala = CF pakar × user │
    │  lalu CF_combine             │
    │  → Berapa tingkat kepastian? │
    └──────────┬───────────────────┘
               │
               ▼
    Output: Daftar penyakit + CF%
            (diurutkan tertinggi)
    ```
    """)

    st.markdown("---")

    st.subheader("Interpretasi Nilai CF")
    st.markdown("""
    | Rentang CF | Interpretasi |
    |:---:|:---|
    | 0.00 – 0.20 | Tidak Pasti |
    | 0.21 – 0.40 | Mungkin |
    | 0.41 – 0.60 | Kemungkinan Besar |
    | 0.61 – 0.80 | Hampir Pasti |
    | 0.81 – 1.00 | Pasti |
    """)


# =============================================
# PAGE: Admin Panel (only for admin role)
# =============================================
elif menu == "Admin Panel" and user_role == "admin":
    st.title("Panel Admin")
    st.markdown("Kelola basis pengetahuan dan akun pengguna sistem pakar.")
    st.markdown("---")

    admin_tab = st.tabs([
        "Kelola Akun",
        "Kelola Penyakit",
        "Kelola Gejala",
        "Kelola Rules CF",
        "Kelola Rules FC",
    ])

    # ===========================================
    # TAB: Kelola Akun
    # ===========================================
    with admin_tab[0]:
        st.subheader("Kelola Akun Pengguna")

        users = get_all_users()
        users_df = pd.DataFrame(users)
        if not users_df.empty:
            display_users = users_df[['id', 'username', 'role', 'nama_lengkap']].copy()
            display_users.columns = ['ID', 'Username', 'Role', 'Nama Lengkap']
            st.dataframe(display_users, use_container_width=True, hide_index=True)
        st.caption(f"Total: {len(users)} akun")

        st.markdown("---")

        # --- Add User ---
        st.markdown("#### Tambah Akun Baru")
        with st.form("add_user", clear_on_submit=True):
            col1, col2 = st.columns(2)
            with col1:
                new_uname = st.text_input("Username", key="new_uname")
                new_upass = st.text_input("Password", type="password", key="new_upass")
            with col2:
                new_urole = st.selectbox("Role", options=["user", "admin"], key="new_urole")
                new_unama = st.text_input("Nama Lengkap", key="new_unama")

            if st.form_submit_button("Tambah Akun", use_container_width=True):
                if not new_uname or not new_upass:
                    st.error("Username dan password harus diisi!")
                elif len(new_upass) < 4:
                    st.error("Password minimal 4 karakter!")
                else:
                    if add_user(new_uname, new_upass, new_urole, new_unama):
                        st.success(f"Akun **{new_uname}** berhasil ditambahkan!")
                        st.rerun()
                    else:
                        st.error(f"Username **{new_uname}** sudah digunakan!")

        st.markdown("---")

        # --- Edit User ---
        st.markdown("#### Edit Akun")
        if users:
            edit_user_select = st.selectbox(
                "Pilih akun:",
                options=[f"[{u['id']}] {u['username']} ({u['role']})" for u in users],
                key="edit_user_select", index=None, placeholder="Pilih akun...",
            )
            if edit_user_select:
                edit_uid = int(edit_user_select.split("]")[0].replace("[", "").strip())
                current_user = next(u for u in users if u['id'] == edit_uid)

                with st.form("edit_user"):
                    col1, col2 = st.columns(2)
                    with col1:
                        edit_uname = st.text_input("Username", value=current_user['username'])
                        edit_upass = st.text_input(
                            "Password Baru (kosongkan jika tidak diubah)",
                            type="password", key="edit_upass"
                        )
                    with col2:
                        role_idx = 0 if current_user['role'] == 'user' else 1
                        edit_urole = st.selectbox("Role", options=["user", "admin"], index=role_idx)
                        edit_unama = st.text_input("Nama Lengkap", value=current_user['nama_lengkap'] or "")

                    if st.form_submit_button("Simpan Perubahan", use_container_width=True):
                        pwd = edit_upass if edit_upass else None
                        if update_user(edit_uid, edit_uname, pwd, edit_urole, edit_unama):
                            st.success(f"Akun **{edit_uname}** berhasil diupdate!")
                            st.rerun()
                        else:
                            st.error("Username sudah digunakan oleh akun lain!")

        st.markdown("---")

        # --- Delete User ---
        st.markdown("#### Hapus Akun")
        if users:
            # Don't allow deleting the current logged-in user
            deletable = [u for u in users if u['id'] != user_info['id']]
            if deletable:
                del_user_select = st.selectbox(
                    "Pilih akun yang akan dihapus:",
                    options=[f"[{u['id']}] {u['username']} ({u['role']})" for u in deletable],
                    key="del_user_select", index=None, placeholder="Pilih akun...",
                )
                if del_user_select:
                    del_uid = int(del_user_select.split("]")[0].replace("[", "").strip())
                    if st.button("Hapus Akun", key="btn_del_user", type="primary"):
                        delete_user(del_uid)
                        st.success("Akun berhasil dihapus!")
                        st.rerun()
            else:
                st.info("Tidak ada akun lain yang bisa dihapus.")

    # ===========================================
    # TAB: Kelola Penyakit
    # ===========================================
    with admin_tab[1]:
        st.subheader("Kelola Data Penyakit")

        st.dataframe(penyakit_df, use_container_width=True, hide_index=True)
        st.caption(f"Total: {len(penyakit_df)} penyakit")
        st.markdown("---")

        # --- Add ---
        st.markdown("#### Tambah Penyakit Baru")
        with st.form("add_penyakit", clear_on_submit=True):
            col1, col2 = st.columns(2)
            with col1:
                new_pid = st.text_input("ID Penyakit", value=get_next_penyakit_id())
            with col2:
                new_pname = st.text_input("Nama Penyakit")

            if st.form_submit_button("Tambah Penyakit", use_container_width=True):
                if not new_pid or not new_pname:
                    st.error("ID dan Nama Penyakit harus diisi!")
                elif add_penyakit(new_pid, new_pname):
                    clear_cache()
                    st.success(f"Penyakit **{new_pname}** ({new_pid}) berhasil ditambahkan!")
                    st.rerun()
                else:
                    st.error(f"ID `{new_pid}` sudah ada!")

        st.markdown("---")

        # --- Edit ---
        st.markdown("#### Edit Penyakit")
        if len(penyakit_df) > 0:
            edit_p = st.selectbox(
                "Pilih penyakit:",
                options=[f"[{r['id_penyakit']}] {r['nama_penyakit']}" for _, r in penyakit_df.iterrows()],
                key="edit_p", index=None, placeholder="Pilih penyakit...",
            )
            if edit_p:
                epid = edit_p.split("]")[0].replace("[", "").strip()
                cur = penyakit_df[penyakit_df['id_penyakit'] == epid].iloc[0]
                with st.form("edit_penyakit"):
                    epname = st.text_input("Nama Penyakit", value=cur['nama_penyakit'])
                    if st.form_submit_button("Simpan", use_container_width=True):
                        if not epname:
                            st.error("Nama tidak boleh kosong!")
                        else:
                            update_penyakit(epid, epname)
                            clear_cache()
                            st.success(f"Penyakit **{epid}** berhasil diupdate!")
                            st.rerun()

        st.markdown("---")

        # --- Delete ---
        st.markdown("#### Hapus Penyakit")
        if len(penyakit_df) > 0:
            del_p = st.selectbox(
                "Pilih penyakit yang akan dihapus:",
                options=[f"[{r['id_penyakit']}] {r['nama_penyakit']}" for _, r in penyakit_df.iterrows()],
                key="del_p", index=None, placeholder="Pilih penyakit...",
            )
            if del_p:
                dpid = del_p.split("]")[0].replace("[", "").strip()
                counts = get_related_rules_count(id_penyakit=dpid)
                if counts['cf'] > 0 or counts['fc'] > 0:
                    st.warning(f"Penyakit ini memiliki **{counts['cf']} rules CF** dan **{counts['fc']} rules FC** terkait. Semua akan dihapus!")
                if st.button("Hapus Penyakit", key="btn_del_p", type="primary"):
                    delete_penyakit(dpid)
                    clear_cache()
                    st.success(f"Penyakit **{dpid}** dan rules terkait berhasil dihapus!")
                    st.rerun()

    # ===========================================
    # TAB: Kelola Gejala
    # ===========================================
    with admin_tab[2]:
        st.subheader("Kelola Data Gejala")

        st.dataframe(gejala_df, use_container_width=True, hide_index=True)
        st.caption(f"Total: {len(gejala_df)} gejala")
        st.markdown("---")

        # --- Add ---
        st.markdown("#### Tambah Gejala Baru")
        with st.form("add_gejala", clear_on_submit=True):
            col1, col2 = st.columns(2)
            with col1:
                new_gid = st.text_input("ID Gejala", value=get_next_gejala_id())
            with col2:
                new_gname = st.text_input("Nama Gejala")

            if st.form_submit_button("Tambah Gejala", use_container_width=True):
                if not new_gid or not new_gname:
                    st.error("ID dan Nama Gejala harus diisi!")
                elif add_gejala(new_gid, new_gname):
                    clear_cache()
                    st.success(f"Gejala **{new_gname}** ({new_gid}) berhasil ditambahkan!")
                    st.rerun()
                else:
                    st.error(f"ID `{new_gid}` sudah ada!")

        st.markdown("---")

        # --- Edit ---
        st.markdown("#### Edit Gejala")
        if len(gejala_df) > 0:
            edit_g = st.selectbox(
                "Pilih gejala:",
                options=[f"[{r['id_gejala']}] {r['nama_gejala']}" for _, r in gejala_df.iterrows()],
                key="edit_g", index=None, placeholder="Pilih gejala...",
            )
            if edit_g:
                egid = edit_g.split("]")[0].replace("[", "").strip()
                cur = gejala_df[gejala_df['id_gejala'] == egid].iloc[0]
                with st.form("edit_gejala"):
                    egname = st.text_input("Nama Gejala", value=cur['nama_gejala'])
                    if st.form_submit_button("Simpan", use_container_width=True):
                        if not egname:
                            st.error("Nama tidak boleh kosong!")
                        else:
                            update_gejala(egid, egname)
                            clear_cache()
                            st.success(f"Gejala **{egid}** berhasil diupdate!")
                            st.rerun()

        st.markdown("---")

        # --- Delete ---
        st.markdown("#### Hapus Gejala")
        if len(gejala_df) > 0:
            del_g = st.selectbox(
                "Pilih gejala yang akan dihapus:",
                options=[f"[{r['id_gejala']}] {r['nama_gejala']}" for _, r in gejala_df.iterrows()],
                key="del_g", index=None, placeholder="Pilih gejala...",
            )
            if del_g:
                dgid = del_g.split("]")[0].replace("[", "").strip()
                counts = get_related_rules_count(id_gejala=dgid)
                if counts['cf'] > 0:
                    st.warning(f"Gejala ini digunakan di **{counts['cf']} rules CF**. Rules terkait juga akan dihapus!")
                if st.button("Hapus Gejala", key="btn_del_g", type="primary"):
                    delete_gejala(dgid)
                    clear_cache()
                    st.success(f"Gejala **{dgid}** dan rules terkait berhasil dihapus!")
                    st.rerun()

    # ===========================================
    # TAB: Kelola Rules CF
    # ===========================================
    with admin_tab[3]:
        st.subheader("Kelola Rules Certainty Factor")

        display_cf = rules_cf_df.merge(penyakit_df, on='id_penyakit', how='left').merge(gejala_df, on='id_gejala', how='left')
        display_cf = display_cf[['id_rule', 'id_penyakit', 'nama_penyakit', 'id_gejala', 'nama_gejala', 'bobot_cf']]
        st.dataframe(display_cf, use_container_width=True, hide_index=True)
        st.caption(f"Total: {len(rules_cf_df)} rules")
        st.markdown("---")

        # --- Add ---
        st.markdown("#### Tambah Rule CF Baru")
        with st.form("add_rule_cf", clear_on_submit=True):
            col1, col2 = st.columns(2)
            with col1:
                new_rid = st.text_input("ID Rule", value=get_next_rule_cf_id(), key="new_cf_rid")
            with col2:
                new_bobot = st.number_input("Bobot CF", 0.0, 1.0, 0.8, 0.1, key="new_cf_bobot")

            col3, col4 = st.columns(2)
            with col3:
                new_cf_p = st.selectbox(
                    "Penyakit:", index=None, placeholder="Pilih penyakit...",
                    options=[f"[{r['id_penyakit']}] {r['nama_penyakit']}" for _, r in penyakit_df.iterrows()],
                    key="new_cf_p",
                )
            with col4:
                new_cf_g = st.selectbox(
                    "Gejala:", index=None, placeholder="Pilih gejala...",
                    options=[f"[{r['id_gejala']}] {r['nama_gejala']}" for _, r in gejala_df.iterrows()],
                    key="new_cf_g",
                )

            if st.form_submit_button("Tambah Rule CF", use_container_width=True):
                if not new_cf_p or not new_cf_g:
                    st.error("Penyakit dan Gejala harus dipilih!")
                else:
                    pid = new_cf_p.split("]")[0].replace("[", "").strip()
                    gid = new_cf_g.split("]")[0].replace("[", "").strip()
                    if check_duplicate_rule_cf(pid, gid):
                        st.error(f"Rule untuk kombinasi {pid} + {gid} sudah ada!")
                    elif add_rule_cf(new_rid, pid, gid, new_bobot):
                        clear_cache()
                        st.success(f"Rule CF **{new_rid}** berhasil ditambahkan!")
                        st.rerun()
                    else:
                        st.error(f"ID Rule `{new_rid}` sudah ada!")

        st.markdown("---")

        # --- Edit ---
        st.markdown("#### Edit Rule CF")
        if len(rules_cf_df) > 0:
            edit_cf = st.selectbox(
                "Pilih rule:",
                options=[f"[{r['id_rule']}] {r['id_penyakit']} ← {r['id_gejala']} (CF: {r['bobot_cf']})" for _, r in rules_cf_df.iterrows()],
                key="edit_cf", index=None, placeholder="Pilih rule...",
            )
            if edit_cf:
                erid = edit_cf.split("]")[0].replace("[", "").strip()
                cur = rules_cf_df[rules_cf_df['id_rule'] == erid].iloc[0]

                with st.form("edit_rule_cf"):
                    col1, col2 = st.columns(2)
                    with col1:
                        p_opts = [f"[{r['id_penyakit']}] {r['nama_penyakit']}" for _, r in penyakit_df.iterrows()]
                        p_idx = next((i for i, o in enumerate(p_opts) if cur['id_penyakit'] in o), 0)
                        ecf_p = st.selectbox("Penyakit:", options=p_opts, index=p_idx, key="ecf_p")
                    with col2:
                        g_opts = [f"[{r['id_gejala']}] {r['nama_gejala']}" for _, r in gejala_df.iterrows()]
                        g_idx = next((i for i, o in enumerate(g_opts) if cur['id_gejala'] in o), 0)
                        ecf_g = st.selectbox("Gejala:", options=g_opts, index=g_idx, key="ecf_g")

                    ecf_bobot = st.number_input("Bobot CF", 0.0, 1.0, float(cur['bobot_cf']), 0.1, key="ecf_bobot")

                    if st.form_submit_button("Simpan", use_container_width=True):
                        pid = ecf_p.split("]")[0].replace("[", "").strip()
                        gid = ecf_g.split("]")[0].replace("[", "").strip()
                        update_rule_cf(erid, pid, gid, ecf_bobot)
                        clear_cache()
                        st.success(f"Rule **{erid}** berhasil diupdate!")
                        st.rerun()

        st.markdown("---")

        # --- Delete ---
        st.markdown("#### Hapus Rule CF")
        if len(rules_cf_df) > 0:
            del_cf = st.selectbox(
                "Pilih rule yang akan dihapus:",
                options=[f"[{r['id_rule']}] {r['id_penyakit']} ← {r['id_gejala']} (CF: {r['bobot_cf']})" for _, r in rules_cf_df.iterrows()],
                key="del_cf", index=None, placeholder="Pilih rule...",
            )
            if del_cf:
                drid = del_cf.split("]")[0].replace("[", "").strip()
                if st.button("Hapus Rule CF", key="btn_del_cf", type="primary"):
                    delete_rule_cf(drid)
                    clear_cache()
                    st.success(f"Rule **{drid}** berhasil dihapus!")
                    st.rerun()

    # ===========================================
    # TAB: Kelola Rules FC
    # ===========================================
    with admin_tab[4]:
        st.subheader("Kelola Rules Forward Chaining")

        display_fc_admin = rules_fc_df.merge(penyakit_df, on='id_penyakit', how='left')
        display_fc_admin = display_fc_admin[['id_rule', 'kondisi_if', 'id_penyakit', 'nama_penyakit']]
        st.dataframe(display_fc_admin, use_container_width=True, hide_index=True)
        st.caption(f"Total: {len(rules_fc_df)} rules")
        st.markdown("---")

        # --- Add ---
        st.markdown("#### Tambah Rule FC Baru")
        st.markdown(
            "Format kondisi: gunakan **AND** atau **OR**. "
            "Contoh: `G011 AND G013 AND G015` atau `G001 OR G002`"
        )
        with st.form("add_rule_fc", clear_on_submit=True):
            col1, col2 = st.columns(2)
            with col1:
                new_fc_rid = st.text_input("ID Rule", value=get_next_rule_fc_id(), key="new_fc_rid")
            with col2:
                new_fc_p = st.selectbox(
                    "Penyakit (THEN):", index=None, placeholder="Pilih penyakit...",
                    options=[f"[{r['id_penyakit']}] {r['nama_penyakit']}" for _, r in penyakit_df.iterrows()],
                    key="new_fc_p",
                )

            st.markdown("**Pilih gejala untuk kondisi IF:**")
            sel_symptoms = st.multiselect(
                "Gejala:",
                options=[f"[{r['id_gejala']}] {r['nama_gejala']}" for _, r in gejala_df.iterrows()],
                key="new_fc_symptoms", placeholder="Pilih gejala...",
                label_visibility="collapsed",
            )
            operator = st.radio("Operator logika:", ["AND", "OR"], horizontal=True, key="new_fc_op")

            if sel_symptoms:
                sids = [s.split("]")[0].replace("[", "").strip() for s in sel_symptoms]
                cond_preview = f" {operator} ".join(sids)
                st.code(f"IF {cond_preview} THEN ...", language=None)
            else:
                cond_preview = ""

            manual_kondisi = st.text_input(
                "Atau ketik kondisi manual (menimpa pilihan di atas):",
                key="new_fc_manual", placeholder="Contoh: G011 AND G013",
            )

            if st.form_submit_button("Tambah Rule FC", use_container_width=True):
                final_kondisi = manual_kondisi.strip() if manual_kondisi.strip() else cond_preview
                if not new_fc_p:
                    st.error("Penyakit harus dipilih!")
                elif not final_kondisi:
                    st.error("Kondisi IF harus diisi!")
                else:
                    # Validate symptom IDs
                    cond_sids = re.findall(r'G\d+', final_kondisi)
                    valid_gids = set(gejala_df['id_gejala'].tolist())
                    invalid = [s for s in cond_sids if s not in valid_gids]
                    if invalid:
                        st.error(f"Gejala tidak valid: {', '.join(invalid)}")
                    else:
                        pid = new_fc_p.split("]")[0].replace("[", "").strip()
                        if add_rule_fc(new_fc_rid, final_kondisi, pid):
                            clear_cache()
                            st.success(f"Rule FC **{new_fc_rid}** berhasil ditambahkan!")
                            st.rerun()
                        else:
                            st.error(f"ID Rule `{new_fc_rid}` sudah ada!")

        st.markdown("---")

        # --- Edit ---
        st.markdown("#### Edit Rule FC")
        if len(rules_fc_df) > 0:
            edit_fc = st.selectbox(
                "Pilih rule:",
                options=[f"[{r['id_rule']}] IF {r['kondisi_if']} THEN {r['id_penyakit']}" for _, r in rules_fc_df.iterrows()],
                key="edit_fc", index=None, placeholder="Pilih rule...",
            )
            if edit_fc:
                erid = edit_fc.split("]")[0].replace("[", "").strip()
                cur = rules_fc_df[rules_fc_df['id_rule'] == erid].iloc[0]

                with st.form("edit_rule_fc"):
                    p_opts = [f"[{r['id_penyakit']}] {r['nama_penyakit']}" for _, r in penyakit_df.iterrows()]
                    p_idx = next((i for i, o in enumerate(p_opts) if cur['id_penyakit'] in o), 0)
                    efc_p = st.selectbox("Penyakit (THEN):", options=p_opts, index=p_idx, key="efc_p")
                    efc_kondisi = st.text_input("Kondisi IF:", value=cur['kondisi_if'], key="efc_kondisi")

                    if st.form_submit_button("Simpan", use_container_width=True):
                        if not efc_kondisi.strip():
                            st.error("Kondisi IF tidak boleh kosong!")
                        else:
                            cond_sids = re.findall(r'G\d+', efc_kondisi)
                            valid_gids = set(gejala_df['id_gejala'].tolist())
                            invalid = [s for s in cond_sids if s not in valid_gids]
                            if invalid:
                                st.error(f"Gejala tidak valid: {', '.join(invalid)}")
                            else:
                                pid = efc_p.split("]")[0].replace("[", "").strip()
                                update_rule_fc(erid, efc_kondisi.strip(), pid)
                                clear_cache()
                                st.success(f"Rule **{erid}** berhasil diupdate!")
                                st.rerun()

        st.markdown("---")

        # --- Delete ---
        st.markdown("#### Hapus Rule FC")
        if len(rules_fc_df) > 0:
            del_fc = st.selectbox(
                "Pilih rule yang akan dihapus:",
                options=[f"[{r['id_rule']}] IF {r['kondisi_if']} THEN {r['id_penyakit']}" for _, r in rules_fc_df.iterrows()],
                key="del_fc", index=None, placeholder="Pilih rule...",
            )
            if del_fc:
                drid = del_fc.split("]")[0].replace("[", "").strip()
                if st.button("Hapus Rule FC", key="btn_del_fc", type="primary"):
                    delete_rule_fc(drid)
                    clear_cache()
                    st.success(f"Rule **{drid}** berhasil dihapus!")
                    st.rerun()


# =============================================
# FOOTER
# =============================================
st.markdown("---")
st.caption(
    "Sistem Pakar Diagnosa Penyakit Pada Bayi — "
    "Metode Forward Chaining & Certainty Factor | "
    "Dibuat dengan Streamlit & Python"
)
