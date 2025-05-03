import pandas as pd

# Load CSV
df = pd.read_csv("footfall_analysis_output.csv")

# Create a flag for rows with any footfall
df['has_footfall'] = (df['avg_weekday_footfall'] > 0) | (df['avg_weekend_footfall'] > 0)

# Group and aggregate
aggregated = (
    df.groupby(['subzone', 'venue_type'])
    .agg({
        'avg_weekday_footfall': 'mean',
        'avg_weekend_footfall': 'mean',
        'planning_area': 'first',
        'region': 'first',
        'has_footfall': 'sum'  # count only rows with footfall
    })
    .rename(columns={'has_footfall': 'number_of_places'})
    .reset_index()
)

# Apply rule: if both footfall averages are 0, number_of_places should also be 0
aggregated.loc[
    (aggregated['avg_weekday_footfall'] == 0) & (aggregated['avg_weekend_footfall'] == 0),
    'number_of_places'
] = 0

# Reorder columns
aggregated = aggregated[[ 
    'subzone', 'planning_area', 'region', 'venue_type', 'avg_weekday_footfall', 'avg_weekend_footfall', 'number_of_places'
]]

# Save to CSV
aggregated.to_csv("aggregated_venue_footfall.csv", index=False)

print("Aggregation complete. Output saved to 'aggregated_venue_footfall.csv'.")
