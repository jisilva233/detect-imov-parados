import streamlit as st
import plotly.express as px
import pandas as pd
from datetime import date

from src.database import get_client, fetch_opportunities, save_opportunities, fetch_listings
from src.analyzer import run_analysis

st.set_page_config(
    page_title="Imóveis Parados — Oportunidades",
    page_icon="🏠",
    layout="wide",
)

ESTADOS_BR = [
    "AC","AL","AM","AP","BA","CE","DF","ES","GO","MA",
    "MG","MS","MT","PA","PB","PE","PI","PR","RJ","RN",
    "RO","RR","RS","SC","SE","SP","TO",
]


@st.cache_data(ttl=300)
def load_data() -> pd.DataFrame:
    client = get_client()
    return fetch_opportunities(client)


try:
    df = load_data()
except Exception as exc:
    st.error(f"Erro ao carregar dados: {exc}")
    st.stop()

if "state" not in df.columns:
    df["state"] = "N/D"

# ---------------------------------------------------------------------------
# Sidebar — Coletar imóveis do Zap Imóveis
# ---------------------------------------------------------------------------

ZAP_CIDADES = {
    "São Paulo / SP":         ("sp+sao-paulo",          "SP"),
    "Rio de Janeiro / RJ":    ("rj+rio-de-janeiro",     "RJ"),
    "Belo Horizonte / MG":   ("mg+belo-horizonte",      "MG"),
    "Curitiba / PR":          ("pr+curitiba",            "PR"),
    "Porto Alegre / RS":      ("rs+porto-alegre",        "RS"),
    "Salvador / BA":          ("ba+salvador",            "BA"),
    "Fortaleza / CE":         ("ce+fortaleza",           "CE"),
    "Recife / PE":            ("pe+recife",              "PE"),
    "Campinas / SP":          ("sp+campinas",            "SP"),
    "Goiânia / GO":           ("go+goiania",             "GO"),
}

st.sidebar.title("🕷️ Coletar do Zap Imóveis")

with st.sidebar.form("form_scraping", clear_on_submit=False):
    cidade_zap = st.selectbox("Cidade", list(ZAP_CIDADES.keys()))
    paginas = st.number_input("Páginas a coletar", min_value=1, max_value=20, value=3)
    buscar_data = st.checkbox("Buscar data real (mais lento)", value=False,
                              help="Visita cada anúncio para extrair a data de publicação original")
    iniciar_scraping = st.form_submit_button("▶ Iniciar Coleta")

if iniciar_scraping:
    city_slug, state_slug = ZAP_CIDADES[cidade_zap]
    with st.sidebar:
        with st.spinner(f"Coletando imóveis de {cidade_zap}…"):
            try:
                import subprocess, sys, os
                project_dir = os.path.dirname(os.path.abspath(__file__))
                cmd = [sys.executable, "scrape_and_analyze.py",
                       "--city", city_slug,
                       "--state", state_slug,
                       "--pages", str(int(paginas))]
                if buscar_data:
                    cmd.append("--fetch-date")
                result = subprocess.run(
                    cmd,
                    capture_output=True, text=True, cwd=project_dir
                )
                if result.returncode == 0:
                    st.sidebar.success(f"✅ Coleta de {cidade_zap} concluída!")
                    st.cache_data.clear()
                    st.session_state["filter_state"] = state_slug
                    st.rerun()
                else:
                    st.sidebar.error(f"Erro: {result.stderr[-500:]}")
            except Exception as exc:
                st.sidebar.error(f"Erro na coleta: {exc}")

st.sidebar.divider()

# ---------------------------------------------------------------------------
# Sidebar — Cadastrar novo imóvel
# ---------------------------------------------------------------------------

st.sidebar.title("➕ Novo Imóvel")

with st.sidebar.form("form_novo_imovel", clear_on_submit=True):
    estado = st.selectbox("Estado", ESTADOS_BR, index=ESTADOS_BR.index("SP"))
    cidade = st.text_input("Cidade / Bairro", placeholder="Ex: Campinas, Copacabana…",
                           autocomplete="off")
    preco = st.text_input("Preço (R$)", placeholder="Ex: 600000", autocomplete="off")
    fotos = st.text_input("Quantidade de fotos", placeholder="Ex: 8", autocomplete="off")
    data_listagem = st.date_input("Data de listagem", value=date.today(), format="DD/MM/YYYY")
    submitted = st.form_submit_button("Cadastrar")

if submitted:
    erros = []
    if not cidade.strip():
        erros.append("Informe a cidade/bairro.")
    try:
        preco_val = float(preco.replace(".", "").replace(",", ".")) if preco.strip() else 0
        if preco_val <= 0:
            erros.append("Informe um preço válido.")
    except ValueError:
        erros.append("Preço inválido — use apenas números.")
        preco_val = 0
    try:
        fotos_val = int(fotos.strip()) if fotos.strip() else 0
        if fotos_val < 0:
            erros.append("Quantidade de fotos inválida.")
    except ValueError:
        erros.append("Fotos inválido — use apenas números inteiros.")
        fotos_val = 0

    if erros:
        for e in erros:
            st.sidebar.error(e)
    else:
        client = get_client()
        client.table("property_listings").insert({
            "state":        estado,
            "neighborhood": cidade.strip(),
            "price":        preco_val,
            "photo_count":  fotos_val,
            "listed_at":    data_listagem.isoformat(),
            "status":       "active",
        }).execute()


        listings = fetch_listings(client)
        opportunities = run_analysis(listings)
        save_opportunities(opportunities, client)

        st.sidebar.success(f"✅ Imóvel em **{cidade.strip()}** cadastrado e análise atualizada.")
        st.cache_data.clear()
        st.rerun()

# ---------------------------------------------------------------------------
# Sidebar — Remover cidade
# ---------------------------------------------------------------------------

st.sidebar.divider()
st.sidebar.title("🗑️ Remover Cidades")

all_cities_for_removal = sorted(df["neighborhood"].dropna().unique())

with st.sidebar.form("form_remover_cidade", clear_on_submit=True):
    cidades_remover = st.multiselect("Selecione as cidades", all_cities_for_removal)
    confirmar = st.form_submit_button("Remover todos os imóveis das cidades selecionadas")

if confirmar and cidades_remover:
    client = get_client()
    for cidade in cidades_remover:
        client.table("property_listings").delete().eq("neighborhood", cidade).execute()
        client.table("listing_opportunities").delete().eq("neighborhood", cidade).execute()

    nomes = ", ".join(f"**{c}**" for c in cidades_remover)
    st.sidebar.success(f"✅ Imóveis removidos de: {nomes}")
    st.cache_data.clear()
    st.rerun()

# ---------------------------------------------------------------------------
# Sidebar — Filtros (começam vazios)
# ---------------------------------------------------------------------------

st.sidebar.divider()
st.sidebar.title("Filtros")

all_states = sorted(s for s in df["state"].dropna().unique() if s in ESTADOS_BR)
default_states = [st.session_state["filter_state"]] if "filter_state" in st.session_state and st.session_state["filter_state"] in all_states else []
selected_states = st.sidebar.multiselect("Estado", all_states, default=default_states)

cities_in_states = sorted(
    df[df["state"].isin(selected_states)]["neighborhood"].dropna().unique()
) if selected_states else []
selected_neighborhoods = st.sidebar.multiselect("Cidade / Bairro", cities_in_states)

only_stagnant = st.sidebar.checkbox("Somente imóveis parados (>120 dias)", value=False)
only_with_link = st.sidebar.checkbox("Somente imóveis com link", value=False)

min_score, max_score = st.sidebar.slider("Score de oportunidade", 0, 100, (0, 100))

top_n = st.sidebar.number_input("Top N no ranking", min_value=5, max_value=100, value=20)

# Se nenhum filtro selecionado, mostra tudo
if not selected_states and not selected_neighborhoods:
    filtered = df.copy()
else:
    mask = pd.Series(True, index=df.index)
    if selected_states:
        mask &= df["state"].isin(selected_states)
    if selected_neighborhoods:
        mask &= df["neighborhood"].isin(selected_neighborhoods)
    filtered = df[mask].copy()

filtered = filtered[filtered["opportunity_score"].between(min_score, max_score)]
if only_stagnant:
    filtered = filtered[filtered["stagnant_listing"]]
if only_with_link:
    if "listing_url" in filtered.columns:
        filtered = filtered[filtered["listing_url"].notna() & filtered["listing_url"].str.startswith("http", na=False)]

# ---------------------------------------------------------------------------
# KPIs
# ---------------------------------------------------------------------------

st.title("🏠 Detector de Imóveis Parados")

col1, col2, col3, col4 = st.columns(4)
col1.metric("Total de imóveis", len(filtered))
col2.metric(
    "Imóveis parados",
    int(filtered["stagnant_listing"].sum()),
    delta=f"{filtered['stagnant_listing'].mean():.0%} do total" if len(filtered) else "0%",
    delta_color="inverse",
)
col3.metric("Score médio", f"{filtered['opportunity_score'].mean():.1f}" if len(filtered) else "0")
col4.metric("Dias médios no mercado", f"{filtered['days_on_market'].mean():.0f}" if len(filtered) else "0")

st.divider()

# ---------------------------------------------------------------------------
# Ranking
# ---------------------------------------------------------------------------

st.subheader(f"🏆 Top {top_n} — Maior Potencial de Melhoria")

top = filtered.nlargest(int(top_n), "opportunity_score")

if not top.empty:
    fig_bar = px.bar(
        top,
        x="opportunity_score",
        y=top["id"].astype(str),
        orientation="h",
        color="opportunity_score",
        color_continuous_scale="RdYlGn_r",
        labels={"opportunity_score": "Score", "y": "ID"},
        hover_data=["neighborhood", "days_on_market", "price", "photo_count"],
        text="opportunity_score",
    )
    fig_bar.update_layout(
        yaxis={"categoryorder": "total ascending"},
        coloraxis_showscale=False,
        height=max(400, int(top_n) * 22),
    )
    st.plotly_chart(fig_bar, use_container_width=True)
else:
    st.info("Nenhum imóvel encontrado com os filtros selecionados.")

# ---------------------------------------------------------------------------
# Gráficos
# ---------------------------------------------------------------------------

col_l, col_r = st.columns(2)

with col_l:
    st.subheader("📊 Distribuição do Score")
    if not filtered.empty:
        fig_hist = px.histogram(
            filtered, x="opportunity_score", nbins=20,
            color_discrete_sequence=["#636EFA"],
            labels={"opportunity_score": "Score"},
        )
        st.plotly_chart(fig_hist, use_container_width=True)

with col_r:
    st.subheader("📍 Score Médio por Bairro")
    if not filtered.empty:
        by_neigh = (
            filtered.groupby("neighborhood")["opportunity_score"]
            .mean().sort_values(ascending=False).reset_index()
        )
        fig_neigh = px.bar(
            by_neigh, x="neighborhood", y="opportunity_score",
            color="opportunity_score", color_continuous_scale="RdYlGn_r",
            labels={"opportunity_score": "Score médio", "neighborhood": "Bairro"},
        )
        fig_neigh.update_layout(coloraxis_showscale=False)
        st.plotly_chart(fig_neigh, use_container_width=True)

# ---------------------------------------------------------------------------
# Scatter
# ---------------------------------------------------------------------------

st.subheader("⏳ Dias no Mercado vs Score de Oportunidade")

if not filtered.empty:
    fig_scatter = px.scatter(
        filtered,
        x="days_on_market", y="opportunity_score",
        color="stagnant_listing",
        color_discrete_map={True: "#EF553B", False: "#636EFA"},
        hover_data=["id", "neighborhood", "price", "photo_count"],
        labels={
            "days_on_market": "Dias no Mercado",
            "opportunity_score": "Score",
            "stagnant_listing": "Parado",
        },
        opacity=0.7,
    )
    fig_scatter.add_vline(
        x=120, line_dash="dash", line_color="orange",
        annotation_text="120 dias", annotation_position="top right",
    )
    st.plotly_chart(fig_scatter, use_container_width=True)

# ---------------------------------------------------------------------------
# Tabela detalhada
# ---------------------------------------------------------------------------

st.subheader("🔍 Detalhamento — Top Imóveis")

if not filtered.empty:
    cols = ["id", "state", "neighborhood", "days_on_market", "photo_count", "price",
            "score_days", "score_photos", "score_price_premium",
            "opportunity_score", "stagnant_listing", "listing_url"]

    # listing_url pode não existir em registros antigos
    if "listing_url" not in filtered.columns:
        filtered["listing_url"] = None

    detail = filtered.nlargest(int(top_n), "opportunity_score")[cols].copy()
    detail["status_label"] = detail.apply(
        lambda r: f"⚠️ Parado ({int(r['days_on_market'])} dias)" if r["stagnant_listing"]
                  else f"✅ Ativo ({int(r['days_on_market'])} dias)",
        axis=1,
    )
    detail["price"] = detail["price"].apply(lambda v: f"R$ {v:,.0f}")
    detail["listing_url"] = detail["listing_url"].apply(
        lambda v: v if isinstance(v, str) and v.startswith("http") else None
    )

    st.dataframe(
        detail.drop(columns=["stagnant_listing", "days_on_market"]).rename(columns={
            "id": "ID", "state": "UF", "neighborhood": "Cidade",
            "photo_count": "Fotos", "price": "Preço",
            "score_days": "Score Tempo", "score_photos": "Score Fotos",
            "score_price_premium": "Score Preço", "opportunity_score": "Score Total",
            "status_label": "Status", "listing_url": "Link",
        }),
        use_container_width=True,
        hide_index=True,
        column_config={
            "Link": st.column_config.LinkColumn("Link", display_text="🔗 Ver anúncio"),
        },
    )
