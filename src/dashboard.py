"""Interactive Streamlit interface for the NGDP energy dataset."""

from html import escape

import altair as alt
import streamlit as st

try:
    from .analytics import calculate_statistics
    from .config import DASHBOARD_STYLE_PATH
    from .dashboard_presenter import (
        ENERGY_COLORS,
        filter_dashboard_data,
        format_energy,
        format_exact_energy,
        format_period,
        latest_change,
        latest_energy_mix,
        monthly_totals,
        renewable_share,
        source_totals,
    )
    from .data_loading import EnergyDataError, load_energy_data
    from .provenance import SourceMetadataError, load_source_metadata
except ImportError:  # Streamlit executes this file as a script from project root.
    from src.analytics import calculate_statistics
    from src.config import DASHBOARD_STYLE_PATH
    from src.dashboard_presenter import (
        ENERGY_COLORS,
        filter_dashboard_data,
        format_energy,
        format_exact_energy,
        format_period,
        latest_change,
        latest_energy_mix,
        monthly_totals,
        renewable_share,
        source_totals,
    )
    from src.data_loading import EnergyDataError, load_energy_data
    from src.provenance import SourceMetadataError, load_source_metadata


st.set_page_config(
    page_title="NGDP — Nordic Green Data Platform",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)


@st.cache_data
def load_dashboard_data():
    """Load validated energy data once per Streamlit cache cycle."""

    return load_energy_data()


@st.cache_data
def load_dashboard_source():
    """Load the structured source record once per Streamlit cache cycle."""

    return load_source_metadata()


def render_section(kicker: str, title: str, description: str) -> None:
    """Render a consistent compact section heading."""

    st.markdown(
        f"""
        <section class="ngdp-section">
          <span class="ngdp-eyebrow">{escape(kicker)}</span>
          <h2>{escape(title)}</h2>
          <p>{escape(description)}</p>
        </section>
        """,
        unsafe_allow_html=True,
    )


def chart_theme(chart: alt.Chart) -> alt.Chart:
    """Apply shared visual settings to an Altair chart."""

    return (
        chart.configure_view(stroke=None)
        .configure_axis(
            domainColor="#244653",
            gridColor="#15333f",
            labelColor="#8fa9b8",
            labelFontSize=10,
            tickColor="#244653",
            titleColor="#8fa9b8",
            titleFontSize=10,
        )
        .configure_legend(
            labelColor="#9fb8c5",
            labelFontSize=10,
            titleColor="#9fb8c5",
            titleFontSize=10,
        )
    )


try:
    data = load_dashboard_data()
    source_metadata = load_dashboard_source()
    stylesheet = DASHBOARD_STYLE_PATH.read_text(encoding="utf-8")
except (FileNotFoundError, EnergyDataError, SourceMetadataError, OSError) as exc:
    st.error(f"Unable to load the validated dashboard assets: {exc}")
    st.stop()

st.markdown(f"<style>{stylesheet}</style>", unsafe_allow_html=True)

snapshot = source_metadata["snapshot"]
latest_date = data["date"].max()
earliest_year = int(data["date"].dt.year.min())
latest_year = int(data["date"].dt.year.max())
available_sources = sorted(data["energy_source"].unique())

retrieved_on = str(snapshot.get("retrieved_on") or "")
retrieved_label = retrieved_on[:10] if len(retrieved_on) >= 10 else "Not recorded"
hash_label = str(snapshot["raw_sha256"])[:12]

with st.sidebar:
    st.markdown("## Explore the dataset")
    st.caption("Change the evidence window without altering the canonical snapshot.")
    selected_sources = st.multiselect(
        "Energy sources",
        available_sources,
        default=available_sources,
    )
    selected_years = st.slider(
        "Period",
        min_value=earliest_year,
        max_value=latest_year,
        value=(max(earliest_year, latest_year - 14), latest_year),
    )
    st.divider()
    st.caption(
        f"Official snapshot · {snapshot['period_start']} → {snapshot['period_end']}"
    )
    st.caption(f"SHA-256 · {hash_label}…")

if not selected_sources:
    st.warning("Select at least one energy source to continue the analysis.")
    st.stop()

filtered = filter_dashboard_data(data, selected_sources, selected_years)
if filtered.empty:
    st.warning("No observations match the selected filters.")
    st.stop()

stats = calculate_statistics(filtered)
change = latest_change(filtered)
change_label = None if change is None else f"{change:+.1%} vs previous month"

st.markdown(
    """
    <div class="ngdp-topline">
      <span>NEXUS SYSTEM // NGDP</span>
      <span class="ngdp-status">Validated snapshot online</span>
    </div>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    """
    <section class="ngdp-hero">
      <div>
        <span class="ngdp-kicker">Norwegian energy intelligence</span>
        <h1>Nordic Green <span>Data Platform</span></h1>
        <p>
          A traceable view of Norway's electricity generation, built from an
          official monthly source and protected by validation, provenance and
          reproducible transformation contracts.
        </p>
      </div>
    </section>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    f"""
    <div class="ngdp-trust">
      <div class="ngdp-trust__item">
        <span class="ngdp-trust__label">Official provider</span>
        <span class="ngdp-trust__value">{escape(str(source_metadata["provider"]))}</span>
      </div>
      <div class="ngdp-trust__item">
        <span class="ngdp-trust__label">Source table</span>
        <span class="ngdp-trust__value">SSB {escape(str(source_metadata["table_id"]))}</span>
      </div>
      <div class="ngdp-trust__item">
        <span class="ngdp-trust__label">Available coverage</span>
        <span class="ngdp-trust__value">{escape(str(snapshot["period_start"]))} — {escape(str(snapshot["period_end"]))}</span>
      </div>
      <div class="ngdp-trust__item">
        <span class="ngdp-trust__label">Snapshot retrieved</span>
        <span class="ngdp-trust__value">{escape(retrieved_label)}</span>
      </div>
    </div>
    """,
    unsafe_allow_html=True,
)

render_section(
    "Live analysis",
    "A compact reading of the selected period",
    "Every indicator reacts to the source and year filters in the control panel.",
)

metric_columns = st.columns(4)
with metric_columns[0]:
    st.metric(
        "Latest monthly output",
        format_energy(stats["latest_month_mwh"]),
        delta=change_label,
        help=(
            f"{stats['period_end']} · {format_exact_energy(stats['latest_month_mwh'])}"
        ),
    )
with metric_columns[1]:
    st.metric(
        "Renewable share",
        f"{renewable_share(filtered):.1%}",
        help="Hydro, wind and solar share in the latest selected month.",
    )
with metric_columns[2]:
    st.metric(
        "Selected-period output",
        format_energy(stats["total_mwh"]),
        help=format_exact_energy(stats["total_mwh"]),
    )
with metric_columns[3]:
    st.metric(
        "Monthly average",
        format_energy(stats["monthly_average_mwh"]),
        help=(
            f"Across {stats['month_count']} months and "
            f"{stats['source_count']} selected sources."
        ),
    )

render_section(
    "Production signal",
    "How the selected system changes over time",
    "Hover to inspect exact monthly values. Charts remain intentionally compact.",
)

monthly = monthly_totals(filtered)
base = alt.Chart(monthly).encode(
    x=alt.X("date:T", title=None, axis=alt.Axis(format="%Y", tickCount=8)),
    tooltip=[
        alt.Tooltip("date:T", title="Month", format="%b %Y"),
        alt.Tooltip("production_mwh:Q", title="Production (MWh)", format=",.0f"),
    ],
)
area = base.mark_area(
    color=alt.Gradient(
        gradient="linear",
        stops=[
            alt.GradientStop(color="#2de2e6", offset=0),
            alt.GradientStop(color="rgba(45, 226, 230, 0.03)", offset=1),
        ],
        x1=1,
        x2=1,
        y1=0,
        y2=1,
    ),
).encode(y=alt.Y("production_mwh:Q", title="MWh", axis=alt.Axis(format="~s")))
line = base.mark_line(color="#78f4f6", strokeWidth=1.7).encode(
    y=alt.Y("production_mwh:Q", title="MWh", axis=alt.Axis(format="~s"))
)
trend_chart = chart_theme((area + line).properties(height=250))
st.altair_chart(trend_chart, width="stretch", theme=None)

chart_columns = st.columns((1, 1.25), gap="medium")
mix = latest_energy_mix(filtered)
totals = source_totals(filtered)
color_domain = list(ENERGY_COLORS)
color_range = [ENERGY_COLORS[source] for source in color_domain]

with chart_columns[0]:
    st.markdown(
        f"""
        <div class="ngdp-panel">
          <h3>Latest energy mix</h3>
          <p>{escape(format_period(filtered["date"].max()))} · selected sources</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    donut = (
        alt.Chart(mix)
        .mark_arc(innerRadius=62, outerRadius=96, cornerRadius=4, padAngle=0.025)
        .encode(
            theta=alt.Theta("production_mwh:Q", stack=True),
            color=alt.Color(
                "energy_source:N",
                title=None,
                scale=alt.Scale(domain=color_domain, range=color_range),
            ),
            tooltip=[
                alt.Tooltip("energy_source:N", title="Source"),
                alt.Tooltip(
                    "production_mwh:Q", title="Production (MWh)", format=",.0f"
                ),
                alt.Tooltip("share:Q", title="Share", format=".1%"),
            ],
        )
        .properties(height=235)
    )
    st.altair_chart(chart_theme(donut), width="stretch", theme=None)

with chart_columns[1]:
    st.markdown(
        """
        <div class="ngdp-panel">
          <h3>Production by source</h3>
          <p>Total contribution inside the selected evidence window</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    bars = (
        alt.Chart(totals)
        .mark_bar(cornerRadiusEnd=5, size=20)
        .encode(
            x=alt.X(
                "production_mwh:Q", title="Production (MWh)", axis=alt.Axis(format="~s")
            ),
            y=alt.Y("energy_source:N", title=None, sort="-x"),
            color=alt.Color(
                "energy_source:N",
                legend=None,
                scale=alt.Scale(domain=color_domain, range=color_range),
            ),
            tooltip=[
                alt.Tooltip("energy_source:N", title="Source"),
                alt.Tooltip(
                    "production_mwh:Q", title="Production (MWh)", format=",.0f"
                ),
            ],
        )
        .properties(height=235)
    )
    st.altair_chart(chart_theme(bars), width="stretch", theme=None)

render_section(
    "Evidence pipeline",
    "From official source to review-ready insight",
    "The interface is the final layer of a guarded, reproducible data path.",
)

st.markdown(
    f"""
    <div class="ngdp-pipeline">
      <div class="ngdp-pipeline__step">
        <b>01 · Source</b>
        <strong>SSB table {escape(str(source_metadata["table_id"]))}</strong>
        <span>Monthly electricity generation released by Statistics Norway.</span>
      </div>
      <div class="ngdp-pipeline__step">
        <b>02 · Contract</b>
        <strong>Schema validation</strong>
        <span>Expected dimensions, units, values and four series are verified.</span>
      </div>
      <div class="ngdp-pipeline__step">
        <b>03 · Integrity</b>
        <strong>SHA-256 fingerprint</strong>
        <span>{escape(hash_label)}… identifies the current raw snapshot.</span>
      </div>
      <div class="ngdp-pipeline__step">
        <b>04 · Transform</b>
        <strong>Canonical dataset</strong>
        <span>{len(data):,} normalized source-month observations are available.</span>
      </div>
      <div class="ngdp-pipeline__step">
        <b>05 · Review</b>
        <strong>Quality gate</strong>
        <span>Automated refreshes become reviewable changes before integration.</span>
      </div>
    </div>
    """,
    unsafe_allow_html=True,
)

render_section(
    "Provenance",
    "The numbers remain connected to their source",
    "Snapshot metadata, licensing and the selected observations are available for inspection.",
)

source_columns = st.columns(3)
with source_columns[0]:
    st.markdown(
        f"""
        <div class="ngdp-source-card">
          <b>Dataset</b>
          <strong>{escape(str(source_metadata["title"]))}</strong>
          <span>Frequency: {escape(str(source_metadata["frequency"]))} · Unit: {escape(str(source_metadata["unit"]))}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )
with source_columns[1]:
    st.markdown(
        f"""
        <div class="ngdp-source-card">
          <b>Snapshot</b>
          <strong>{escape(str(snapshot["period_start"]))} → {escape(str(snapshot["period_end"]))}</strong>
          <span>{int(snapshot["record_count"]):,} records · verified {escape(str(snapshot["verified_on"]))}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )
with source_columns[2]:
    license_record = source_metadata["license"]
    st.markdown(
        f"""
        <div class="ngdp-source-card">
          <b>License</b>
          <strong>{escape(str(license_record["identifier"]))}</strong>
          <span>{escape(str(license_record["name"]))}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

st.link_button(
    "Open the official Statistics Norway table",
    str(source_metadata["table_url"]),
)

with st.expander(f"Inspect {len(filtered):,} selected observations"):
    display_data = filtered.copy()
    display_data["date"] = display_data["date"].dt.strftime("%Y-%m")
    display_data = display_data.rename(
        columns={
            "energy_source": "Energy source",
            "date": "Month",
            "production_mwh": "Production (MWh)",
        }
    )
    st.dataframe(
        display_data,
        width="stretch",
        hide_index=True,
        column_config={
            "Production (MWh)": st.column_config.NumberColumn(format="localized")
        },
    )
