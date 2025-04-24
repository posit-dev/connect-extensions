#
# Training for fastapitableau-example.
# Reads clean-orders.csv.
# Writes model.joblib.
#

import pandas as pd
from sklearn.linear_model import LinearRegression
from joblib import dump

# Read in data
data = pd.read_csv("clean-orders.csv")

# Define new features and training data
data["ship_diff"] = data["days_to_ship_actual"] - data["days_to_ship_scheduled"]
train_columns = [
    "ship_diff",
    "quantity",
    "sales",
    "discount",
]
train_data = data[train_columns]

# Fit linear regression model to predict profit
reg = LinearRegression().fit(train_data, data.profit)
reg.predict(train_data)
data["predicted_profit"] = reg.predict(train_data)

# Write the model for use by the API.
dump(reg, "model.joblib")
