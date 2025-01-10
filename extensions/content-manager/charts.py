import matplotlib.pyplot as plt
import pandas as pd

def ViewsChart():
    # Sample data: dates and corresponding views
    data = {
        "date": pd.to_datetime(
            [
                "2025-01-01",
                "2025-11-02",
                "2025-01-03",
                "2025-01-04",
                "2025-01-05",
                "2025-03-10",
                "2025-01-12",
                "2025-01-15",
                "2025-01-20",
                "2025-01-25",
            ]
        ),
        "views": [150, 200, 170, 220, 300, 250, 190, 400, 380, 420],
    }

    df = pd.DataFrame(data)
    date_span = (df["date"].max() - df["date"].min()).days

    # Grouping logic based on the date span
    if date_span <= 7:  # Daily
        group_freq = "D"
    elif date_span <= 30:  # Weekly
        group_freq = "W"
    else:  # Monthly
        group_freq = "M"

    # Group by the chosen frequency and sum views
    df_grouped = df.set_index("date").resample(group_freq).sum().reset_index()

    # Plotting the histogram
    plt.figure(figsize=(10, 6))
    plt.bar(
        df_grouped["date"].dt.strftime("%b '%y"), df_grouped["views"], color="skyblue"
    )

    plt.xticks(rotation=45)
    plt.grid(axis="y", linestyle="--", alpha=0.7)

    return plt.gcf()
