"""Streamlit interface for the current NGDP energy dataset."""

import streamlit as st

try:
    from .analytics import calculate_statistics
    from .data_loading import EnergyDataError, load_energy_data
    from .provenance import SourceMetadataError, load_source_metadata
except ImportError:  # Streamlit executes this file as a script.
    from analytics import calculate_statistics
    from data_loading import EnergyDataError, load_energy_data
    from provenance import SourceMetadataError, load_source_metadata


st.set_page_config(
    page_title="NGDP — Nordic Green Data Platform",
    page_icon="🌱",
    layout="wide",
)


@st.cache_data
def load_dashboard_data():
    """Load validated energy data once per Streamlit cache cycle."""

    return load_energy_data()


@st.cache_data
def load_dashboard_source():
    """Load the structured source record once per Streamlit cache cycle."""

    return load_source_metadata()


def format_compact_mwh(value: float) -> str:
    """Format large production values without truncating metric cards."""

    absolute_value = abs(value)
    if absolute_value >= 1_000_000_000:
        formatted = f"{value / 1_000_000_000:.2f} bi"
    elif absolute_value >= 1_000_000:
        formatted = f"{value / 1_000_000:.2f} mi"
    elif absolute_value >= 1_000:
        formatted = f"{value / 1_000:.2f} mil"
    else:
        formatted = f"{value:.0f}"

    return f"{formatted.replace('.', ',')} MWh"


def format_exact_mwh(value: float) -> str:
    """Format an exact MWh value using Portuguese thousands separators."""

    return f"{value:,.0f}".replace(",", ".") + " MWh"


try:
    df = load_dashboard_data()
    source_metadata = load_dashboard_source()
except (FileNotFoundError, EnergyDataError, SourceMetadataError) as exc:
    st.error(f"Não foi possível carregar os dados: {exc}")
    st.stop()

st.caption("NEXUS SYSTEM // NGDP")
st.title("Nordic Green Data Platform")
st.subheader("Norway Energy Dashboard")

latest_date = df["date"].max()
latest_period = f"{latest_date.month:02d}/{latest_date.year}"
retrieved_on = str(source_metadata["snapshot"].get("retrieved_on") or "")
retrieved_label = ""
if len(retrieved_on) >= 10:
    year, month, day = retrieved_on[:10].split("-")
    retrieved_label = f" · Coletado em {day}/{month}/{year}"
st.caption(
    f"Fonte: {source_metadata['provider']} · "
    f"Tabela {source_metadata['table_id']} · "
    f"Snapshot disponível até {latest_period}{retrieved_label}."
)

sources = sorted(df["energy_source"].unique())
selected_source = st.selectbox(
    "Fonte de energia",
    sources,
)

source_df = df[df["energy_source"] == selected_source]
years = sorted(source_df["date"].dt.year.unique())
selected_year = st.selectbox(
    "Ano inicial",
    years,
)

df_filtered = source_df[source_df["date"].dt.year >= selected_year]

stats = calculate_statistics(df_filtered)

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric(
        "Produção total",
        format_compact_mwh(stats["total_mwh"]),
        help=f"Valor exato: {format_exact_mwh(stats['total_mwh'])}",
    )

with col2:
    st.metric(
        "Média mensal",
        format_compact_mwh(stats["monthly_average_mwh"]),
        help=(
            "Média calculada após consolidar os valores de cada mês. "
            f"Valor exato: {format_exact_mwh(stats['monthly_average_mwh'])}"
        ),
    )

with col3:
    st.metric(
        "Máximo mensal",
        format_compact_mwh(stats["monthly_peak_mwh"]),
        help=f"Valor exato: {format_exact_mwh(stats['monthly_peak_mwh'])}",
    )

with col4:
    st.metric(
        "Mês mais recente",
        format_compact_mwh(stats["latest_month_mwh"]),
        help=(
            f"Período: {stats['period_end']}. "
            f"Valor exato: {format_exact_mwh(stats['latest_month_mwh'])}"
        ),
    )

st.subheader(f"Histórico de produção — {selected_source}")
if len(df_filtered) > 1:
    st.line_chart(
        df_filtered,
        x="date",
        y="production_mwh",
    )
else:
    st.info("Existe apenas um período disponível para esta combinação de filtros.")

st.subheader("Dados filtrados")
st.dataframe(df_filtered, width="stretch", hide_index=True)
