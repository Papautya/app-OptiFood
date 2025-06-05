import pandas as pd


def load_historical_data(path: str = "Dataset/food_waste.csv") -> pd.DataFrame:
    """
    Carga el dataset histórico de desperdicios.
    El CSV debe contener columnas:
      Country, Year, Food Category, Total Waste (Tons), Economic Loss (Million $),
      Avg Waste per Capita (Kg), Population (Million), Household Waste (%).
    """
    df = pd.read_csv(path)
    return df
  