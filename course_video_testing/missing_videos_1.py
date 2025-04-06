import dash
from dash import dcc, html, dash_table
from dash.dependencies import Input, Output
import polars as pl
import pandas as pd

# Load Data
df = pl.read_parquet("missing_videos.parquet")

# Ensure 'Course Name' column is available
if "Course Name" not in df.columns:
    raise ValueError("The column 'Course Name' is not present in the DataFrame.")

# Get unique course names
course_names = ["All"] + sorted(df["Course Name"].unique().to_list())

# Define column styles to prevent resizing
column_style = {
    "minWidth": "150px",  # Minimum width
    "maxWidth": "150px",  # Maximum width (prevents resizing)
    "width": "150px",  # Fixed width
    "overflow": "hidden",
    "textOverflow": "ellipsis",
    "whiteSpace": "nowrap",
}

# Initialize Dash app
app = dash.Dash(__name__)

app.layout = html.Div([
    html.Label("Class:"),
    dcc.Dropdown(
        id="class-dropdown",
        options=[{"label": name, "value": name} for name in course_names],
        value="All"
    ),

    dash_table.DataTable(
        id="data-table",
        columns=[{"name": col, "id": col} for col in df.columns],  # Columns remain the same
        data=df.head(20).to_pandas().to_dict("records"),
        page_size=20,
        sort_action="custom",  # Enables manual sorting
        sort_mode="single",  # Allows sorting by one column at a time
        fixed_columns={"headers": True, "data": 0},  # Fix column sizes
        style_table={"overflowX": "auto"},
        style_cell=column_style  # Apply fixed column width
    )
])

@app.callback(
    Output("data-table", "data"),
    Input("class-dropdown", "value"),
    Input("data-table", "sort_by")  # Handles sorting
)
def update_table(selected_class, sort_by):
    # Clone the DataFrame to avoid modifying the original
    filtered_df = df.clone()
    
    # Filter by selected class
    if selected_class != "All":
        filtered_df = filtered_df.filter(filtered_df["Course Name"] == selected_class)

    # Handle sorting when user clicks a column
    if sort_by and len(sort_by) > 0:
        sort_column = sort_by[0]["column_id"]
        ascending = sort_by[0]["direction"] == "asc"
        filtered_df = filtered_df.sort(by=[sort_column], descending=[not ascending])

    # Convert to Pandas for Dash table compatibility
    return filtered_df.head(20).to_pandas().to_dict("records")

# Run the app
if __name__ == "__main__":
    app.run_server(debug=True)
