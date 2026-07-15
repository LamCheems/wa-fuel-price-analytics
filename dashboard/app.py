import math
from pathlib import Path

import pandas as pd
import streamlit as st


st.set_page_config(
    page_title="WA Fuel Price Analytics",
    page_icon="⛽",
    layout="wide"
)

DATA_PATH = Path("data/processed/perth_ulp_2026_04_to_06.csv")


@st.cache_data
def load_data() -> pd.DataFrame:
    if not DATA_PATH.exists():
        raise FileNotFoundError(
            f"Processed data file not found: {DATA_PATH}"
        )

    return pd.read_csv(
        DATA_PATH,
        parse_dates=["date"]
    )

try:
    df = load_data()
except FileNotFoundError as error:
    st.error(str(error))
    st.stop()

st.title("WA Fuel Price Analytics")

st.write(
    "Explore Perth ULP price trends, suburbs, brands, "
    "and fuel stations."
)

st.caption(
    f"Data coverage: "
    f"{df['date'].min().strftime('%d %b %Y')} to "
    f"{df['date'].max().strftime('%d %b %Y')} · "
    f"{df['station_id'].nunique():,} stations · "
    f"{len(df):,} price records"
)

st.sidebar.header("Filters")

selected_suburbs = st.sidebar.multiselect(
    "Select suburbs",
    options=sorted(df["suburb"].dropna().unique()),
    key="suburb_filter"
)

selected_brands = st.sidebar.multiselect(
    "Select brands",
    options=sorted(df["brand"].dropna().unique()),
    key="brand_filter"
)

date_range = st.sidebar.date_input(
    "Select date range",
    value=(
        df["date"].min().date(),
        df["date"].max().date()
    ),
    key="date_filter"
)
def reset_filters() -> None:
    st.session_state["suburb_filter"] = []
    st.session_state["brand_filter"] = []
    st.session_state["date_filter"] = (
        df["date"].min().date(),
        df["date"].max().date()
    )
st.sidebar.button(
    "Reset filters",
    on_click=reset_filters
)

filtered_df = df.copy()

if selected_suburbs:
    filtered_df = filtered_df[
        filtered_df["suburb"].isin(selected_suburbs)
    ]

if selected_brands:
    filtered_df = filtered_df[
        filtered_df["brand"].isin(selected_brands)
    ]

if len(date_range) == 2:
    start_date, end_date = date_range

    filtered_df = filtered_df[
        filtered_df["date"].between(
            pd.Timestamp(start_date),
            pd.Timestamp(end_date)
        )
    ]

if filtered_df.empty:
    st.warning("No records match the selected filters.")
    st.stop()

average_price = filtered_df["price_cpl"].mean()
minimum_price = filtered_df["price_cpl"].min()
maximum_price = filtered_df["price_cpl"].max()
station_count = filtered_df["station_id"].nunique()
price_spread = maximum_price - minimum_price

col1, col2, col3, col4, col5 = st.columns(5)

col1.metric("Average price", f"{average_price:.1f} cpl")
col2.metric("Lowest price", f"{minimum_price:.1f} cpl")
col3.metric("Highest price", f"{maximum_price:.1f} cpl")
col4.metric("Price spread", f"{price_spread:.1f} cpl")
col5.metric("Stations", f"{station_count:,}")

saving_vs_average_60l = (
    average_price - minimum_price
) * 60 / 100

st.caption(
    f"Choosing the lowest-priced station instead of "
    f"the average station could save approximately "
    f"${saving_vs_average_60l:.2f} on a 60-litre fill."
)

st.subheader("Key Insights")

weekday_order = [
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
    "Saturday",
    "Sunday"
]

weekday_summary = (
    filtered_df.groupby("day_of_week", as_index=False)
    .agg(average_price=("price_cpl", "mean"))
)

weekday_summary["day_of_week"] = pd.Categorical(
    weekday_summary["day_of_week"],
    categories=weekday_order,
    ordered=True
)

weekday_summary = weekday_summary.sort_values("day_of_week")

cheapest_weekday = weekday_summary.loc[
    weekday_summary["average_price"].idxmin()
]

brand_summary = (
    filtered_df.groupby("brand", as_index=False)
    .agg(
        average_price=("price_cpl", "mean"),
        observations=("price_cpl", "size"),
        station_count=("station_id", "nunique")
    )
)

brand_summary = brand_summary[
    (brand_summary["observations"] >= 20)
    & (brand_summary["station_count"] >= 2)
]

suburb_summary_insight = (
    filtered_df.groupby("suburb", as_index=False)
    .agg(
        average_price=("price_cpl", "mean"),
        observations=("price_cpl", "size"),
        station_count=("station_id", "nunique")
    )
)

suburb_summary_insight = suburb_summary_insight[
    (suburb_summary_insight["observations"] >= 20)
    & (suburb_summary_insight["station_count"] >= 2)
]

insight_col1, insight_col2, insight_col3 = st.columns(3)

insight_col1.info(
    f"Cheapest weekday: "
    f"{cheapest_weekday['day_of_week']} "
    f"({cheapest_weekday['average_price']:.1f} cpl)"
)

if not brand_summary.empty:
    cheapest_brand = brand_summary.loc[
        brand_summary["average_price"].idxmin()
    ]

    insight_col2.info(
        f"Cheapest brand: "
        f"{cheapest_brand['brand']} "
        f"({cheapest_brand['average_price']:.1f} cpl)"
    )
else:
    insight_col2.info(
        "Not enough brand data for the selected filters."
    )

if not suburb_summary_insight.empty:
    cheapest_suburb = suburb_summary_insight.loc[
        suburb_summary_insight["average_price"].idxmin()
    ]

    insight_col3.info(
        f"Cheapest suburb: "
        f"{cheapest_suburb['suburb']} "
        f"({cheapest_suburb['average_price']:.1f} cpl)"
    )
else:
    insight_col3.info(
        "Not enough suburb data for the selected filters."
    )

st.divider()
st.header("Price Analysis")

st.subheader("Daily average ULP price")

daily_price = (
    filtered_df.groupby("date", as_index=False)
    .agg(average_price=("price_cpl", "mean"))
    .set_index("date")
)

st.line_chart(daily_price)

st.subheader("Top 10 Consistently Cheap Stations")

# Ensure each station contributes only one price per day.
station_daily_price = (
    filtered_df.groupby(
        [
            "date",
            "station_id",
            "station_name",
            "brand",
            "suburb"
        ],
        as_index=False
    )
    .agg(
        price_cpl=("price_cpl", "mean")
    )
)

# Calculate the selected market's daily average price.
market_daily_average = (
    station_daily_price.groupby("date", as_index=False)
    .agg(
        market_average_price=("price_cpl", "mean")
    )
)

station_daily_price = station_daily_price.merge(
    market_daily_average,
    on="date",
    how="left"
)

station_daily_price["difference_from_daily_avg"] = (
    station_daily_price["price_cpl"]
    - station_daily_price["market_average_price"]
)

station_daily_price["below_daily_average"] = (
    station_daily_price["difference_from_daily_avg"] < 0
)

station_summary = (
    station_daily_price.groupby(
        [
            "station_id",
            "station_name",
            "brand",
            "suburb"
        ],
        as_index=False
    )
    .agg(
        average_price=("price_cpl", "mean"),
        average_difference_from_market=(
            "difference_from_daily_avg",
            "mean"
        ),
        below_market_days=(
            "below_daily_average",
            "sum"
        ),
        days_observed=("date", "nunique")
    )
)

station_summary["below_market_percentage"] = (
    station_summary["below_market_days"]
    / station_summary["days_observed"]
    * 100
)

selected_day_count = station_daily_price["date"].nunique()

minimum_required_days = max(
    1,
    math.ceil(selected_day_count * 0.7)
)

st.caption(
    f"Stations must have data for at least "
    f"{minimum_required_days} of "
    f"{selected_day_count} selected days."
)

eligible_stations = station_summary[
    station_summary["days_observed"] >= minimum_required_days
].copy()

top_stations = (
    eligible_stations.sort_values(
        [
            "below_market_percentage",
            "average_difference_from_market",
            "average_price"
        ],
        ascending=[False, True, True]
    )
    .head(10)
)

if top_stations.empty:
    st.info(
        "No stations have enough observations "
        "for the selected filters."
    )
else:
    display_stations = top_stations[
        [
            "station_name",
            "brand",
            "suburb",
            "average_price",
            "below_market_percentage",
            "average_difference_from_market",
            "days_observed"
        ]
    ].copy()

    display_stations = display_stations.rename(
        columns={
            "station_name": "Station",
            "brand": "Brand",
            "suburb": "Suburb",
            "average_price": "Average Price (cpl)",
            "below_market_percentage": (
                "Days Below Market (%)"
            ),
            "average_difference_from_market": (
                "Difference from Market (cpl)"
            ),
            "days_observed": "Days Observed"
        }
    )

    display_stations["Average Price (cpl)"] = (
        display_stations["Average Price (cpl)"].round(1)
    )

    display_stations["Days Below Market (%)"] = (
        display_stations[
            "Days Below Market (%)"
        ].round(1)
    )

    display_stations["Difference from Market (cpl)"] = (
        display_stations[
            "Difference from Market (cpl)"
        ].round(1)
    )
    st.caption(
        "A negative market difference means the station "
        "was cheaper than the selected daily market average."
    )
    
    st.dataframe(
        display_stations,
        use_container_width=True,
        hide_index=True
    )

    best_station = top_stations.iloc[0]

    difference = (
        best_station["average_difference_from_market"]
    )

    if difference < 0:
        saving_for_60l = abs(difference) * 60 / 100

        st.success(
            f"{best_station['station_name']} in "
            f"{best_station['suburb']} was below the "
            f"selected market average on "
            f"{best_station['below_market_percentage']:.1f}% "
            f"of observed days. It was approximately "
            f"{abs(difference):.1f} cpl cheaper than market, "
            f"equivalent to ${saving_for_60l:.2f} "
            f"per 60-litre fill."
    )

st.subheader("Top 10 cheapest suburbs")

suburb_summary = (
    filtered_df.groupby("suburb", as_index=False)
    .agg(
        average_price=("price_cpl", "mean"),
        station_count=("station_id", "nunique"),
        observations=("price_cpl", "size")
    )
)

suburb_summary = (
    suburb_summary[
        (suburb_summary["station_count"] >= 2)
        & (suburb_summary["observations"] >= 100)
    ]
    .sort_values("average_price")
    .head(10)
)

if suburb_summary.empty:
    st.info(
        "Not enough suburb data for the selected filters."
    )
else:
    st.bar_chart(
        suburb_summary.set_index("suburb")["average_price"]
    )

st.subheader("Average price by brand")

brand_chart = (
    filtered_df.groupby("brand", as_index=False)
    .agg(
        average_price=("price_cpl", "mean"),
        station_count=("station_id", "nunique"),
        observations=("price_cpl", "size")
    )
)

brand_chart = (
    brand_chart[
        (brand_chart["station_count"] >= 2)
        & (brand_chart["observations"] >= 20)
    ]
    .sort_values("average_price")
)

if brand_chart.empty:
    st.info(
        "Not enough brand data for the selected filters."
    )
else:
    st.bar_chart(
        brand_chart.set_index("brand")["average_price"]
    )

with st.expander("How the analysis works"):
    st.markdown(
        """
        - **Daily average price** is calculated from all stations
          matching the selected filters.
        - **Consistently cheap stations** are ranked by the
          percentage of observed days they were below the daily
          market average.
        - Stations must have data for at least **70% of selected
          days** to be included in the ranking.
        - A negative **Difference from Market** means the station
          was cheaper than the selected daily average.
        - Fuel savings are estimated using cents per litre and the
          selected tank size.
        """
    )

st.divider()
st.header("Data Explorer")

with st.expander("View and download filtered records"):
    st.caption(
        f"Showing {len(filtered_df):,} records from "
        f"{filtered_df['station_id'].nunique():,} stations."
    )

    download_df = filtered_df[
        [
            "date",
            "station_name",
            "brand",
            "suburb",
            "price_cpl"
        ]
    ].sort_values(
        ["date", "price_cpl"],
        ascending=[False, True]
    )

    st.dataframe(
        download_df,
        use_container_width=True,
        hide_index=True
    )

    csv_data = download_df.to_csv(
        index=False
    ).encode("utf-8")

    download_file_name = (
        f"perth_ulp_"
        f"{filtered_df['date'].min().date()}_to_"
        f"{filtered_df['date'].max().date()}.csv"
    )

    st.download_button(
        label="Download filtered data as CSV",
        data=csv_data,
        file_name=download_file_name,
        mime="text/csv"
    )

st.divider()
st.header("Savings Tools")

st.subheader("Fuel Saving Calculator")
calc_col1, calc_col2, calc_col3 = st.columns(3)

tank_size = calc_col1.number_input(
    "Tank size (litres)",
    min_value=1.0,
    value=60.0,
    step=1.0
)

current_price = calc_col2.number_input(
    "Current price (cpl)",
    min_value=0.0,
    value=185.9,
    step=0.1
)

alternative_price = calc_col3.number_input(
    "Alternative price (cpl)",
    min_value=0.0,
    value=169.9,
    step=0.1
)

# Calculate saved price
saving = (
    current_price - alternative_price
) * tank_size / 100

# Result
if saving > 0:
    st.success(
        f"Estimated saving: ${saving:.2f}"
    )
elif saving == 0:
    st.info(
        "Both fuel prices are the same."
    )
else:
    st.warning(
        f"The alternative station would cost "
        f"${abs(saving):.2f} more."
    )

st.divider()

st.caption(
    "WA Fuel Price Analytics · Built with Python, pandas, "
    "and Streamlit using FuelWatch data."
)