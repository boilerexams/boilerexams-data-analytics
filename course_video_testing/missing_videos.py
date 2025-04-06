import marimo as mo
import polars as pl

#load Missing Videos Parquet
df = pl.read_parquet("missing_videos.parquet")

class_dropdown = mo.ui.dropdown(
    options = ["All"] + sorted(df["Course Name"].unique().to_list()),
    label="Class"
)
columns_sort_dropdown = mo.ui.dropdown(
    options= ["Average Percent Correct", "Total Submissions", "Correct Submissions"],
    label="Sort Column"
)
sort_order_switch = mo.ui.switch(
    label = "Sorting Direction"
).style(
    on_color="green",  # Green for ascending
    off_color="red",   # Red for descending
    on_text="Ascending",
    off_text="Descending"
)

output_area = mo.ui.table()

def update_table():
    selected_class = class_dropdown.value
    sort_column = columns_sort_dropdown.value
    sort_order = sort_order_switch.value

    filtered_df = df.clone()
    if selected_class != "All":
        filtered_df = filtered_df.filter(filtered_df["Course Name"] == selected_class)

    if sort_column:
        filtered_df = filtered_df.sort(by=[sort_column], descending=[not sort_order])

    output_area.update(filtered_df.head(20).to_pandas())

update_table()


# Arrange UI components into a layout
layout = mo.ui.vbox([
    class_dropdown,
    columns_sort_dropdown,
    sort_order_switch,
    output_area
])

# Show the UI
layout.show()