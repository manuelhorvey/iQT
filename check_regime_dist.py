import pandas as pd
from src.intelligence.data_loader import DataManager
from src.intelligence.features import FeatureEngineer
from src.intelligence.regime import RegimeDetector

manager = DataManager(tickers=["EURUSD=X"])
raw = manager.get_data(period="5y")["EURUSD=X"]
fe = FeatureEngineer(raw)
df = fe.generate_features()
rd = RegimeDetector()
df = rd.fit_predict(df)

print("\nRegime Distribution:")
print(df["Regime_Label"].value_counts())
print("\nRegime Mean Returns:")
print(df.groupby("Regime_Label")["Returns"].mean())
