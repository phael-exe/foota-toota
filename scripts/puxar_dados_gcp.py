import pandas as pd

# Carrega o Brasileirão completo direto do bucket público:
url = "https://storage.googleapis.com/foota-toota-505511/bronze/brasileirao_historico/campeonato_brasileiro_full.csv"
df_brasileirao = pd.read_csv(url)
print(df_brasileirao.head())
