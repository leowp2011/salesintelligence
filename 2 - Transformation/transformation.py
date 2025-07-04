import os
import time
import dask.dataframe as dd
import pandas as pd
import sqlite3
import pyarrow.parquet as pq
import pyarrow as pa
from sqlalchemy import create_engine

# === Caminhos ===
input_path = "../inputs"
db_path = "../1 - Extract & Load/dados-publicos/cnpj.db"
bronze_path = "../intermediarios/bronze"
silver_path = "../intermediarios/silver"
gold_path = "../outputs/gold"

os.makedirs(bronze_path, exist_ok=True)
os.makedirs(silver_path, exist_ok=True)
os.makedirs(gold_path, exist_ok=True)

# Conexão SQLite
conn = sqlite3.connect(db_path)
engine = create_engine(f"sqlite:///{db_path}")

# === Bronze: Extração com Dask via pandas chunks ===
start = time.time()
query = """
    SELECT cnpj, cnae_fiscal, municipio, cnpj_basico, nome_fantasia
    FROM estabelecimento
    WHERE situacao_cadastral = '02'
"""
chunks = pd.read_sql_query(query, conn, chunksize=50_000)
dfs = [dd.from_pandas(chunk, npartitions=1) for chunk in chunks]
estab_dask = dd.concat(dfs)
bronze_file = os.path.join(bronze_path, "estabelecimento_clean.parquet")
estab_dask.to_parquet(bronze_file, write_index=False)
bronze_time = time.time() - start
print(f"Tempo para criar o arquivo bronze: {bronze_time:.2f} segundos")

# === Silver: CNAEs dos clientes ===
start = time.time()
vendas = pd.read_csv(os.path.join(input_path, "vendas.csv"), dtype={"cnpj": str})
clientes_cnpjs = vendas["cnpj"].dropna().unique().tolist()
estab_filtered_pd = dd.read_parquet(bronze_file).compute()
cnaes_primarios = estab_filtered_pd[estab_filtered_pd["cnpj"].isin(clientes_cnpjs)]["cnae_fiscal"].dropna().unique().tolist()
pd.DataFrame({"cnae": sorted(cnaes_primarios)}).to_parquet(os.path.join(silver_path, "clientes_cnaes.parquet"), index=False)
silver_cnaes_time = time.time() - start
print(f"Tempo para criar o arquivo silver de CNAEs: {silver_cnaes_time:.2f} segundos")

# === Silver: CNPJs alvo ===
start = time.time()
cnpjs_alvo = estab_filtered_pd[estab_filtered_pd["cnae_fiscal"].isin(cnaes_primarios)]["cnpj"].dropna().unique()
pd.DataFrame({"cnpj": sorted(cnpjs_alvo)}).to_parquet(os.path.join(silver_path, "cnpjs_alvo.parquet"), index=False)
silver_cnpjs_time = time.time() - start
print(f"Tempo para criar o arquivo silver de CNPJs alvo: {silver_cnpjs_time:.2f} segundos")

# === Gold: Recomendação de produtos
# Agrupa e soma o valor por CNPJ e produto
agrupado = (
    vendas.groupby(["cnpj", "it-codigo", "familia", "familia_comercial"])["valor"]
    .sum()
    .reset_index()
)

# Rankeia os produtos por CNPJ, do maior para o menor
agrupado["rank"] = agrupado.groupby("cnpj")["valor"].rank(method="first", ascending=False)

# Mantém apenas os top 5
top5 = agrupado[agrupado["rank"] <= 5].drop(columns="rank")

# Salva no gold como nova fato
top5.to_parquet(os.path.join(gold_path, "fato_recomendacao_produto.parquet"), index=False)

# === Gold: Join com as empresas ===
start = time.time()
empresas = pd.read_sql("SELECT cnpj_basico, razao_social, porte_empresa FROM empresas", conn)
simples = pd.read_sql("""
    SELECT cnpj_basico,
           CASE WHEN opcao_mei = 'S' THEN 1
                WHEN opcao_simples = 'S' THEN 2
                ELSE 3 END AS id_regime_tributario
    FROM simples
""", conn)

leads = pd.read_csv(os.path.join(input_path, "leads.csv"), dtype={"cnpj": str})
leads_cnpjs = set(leads["cnpj"].dropna().unique())
clientes_cnpjs = set(vendas["cnpj"].dropna().unique())

fato = estab_filtered_pd[estab_filtered_pd["cnpj"].isin(cnpjs_alvo)].copy()
fato = fato.merge(empresas, on="cnpj_basico", how="left")
fato = fato.merge(simples, on="cnpj_basico", how="left")
fato["possui_lead"] = fato["cnpj"].isin(leads_cnpjs).astype(int)
fato["atual_cliente"] = fato["cnpj"].isin(clientes_cnpjs).astype(int)
fato["porte_empresa"] = fato["porte_empresa"].fillna("00")
fato.to_parquet(os.path.join(gold_path, "fato_empresas.parquet"), index=False)
gold_fato_time = time.time() - start
print(f"Tempo para criar o arquivo gold de fato_empresas: {gold_fato_time:.2f} segundos")

# === Dimensões CNAE e Município e Regime Tributário ===
start = time.time()
cnae = pd.read_sql("SELECT codigo, descricao FROM cnae", conn)
cnae["divisao"] = cnae["codigo"].str[:2].astype(int)

def mapear_secao(div):
    if 1 <= div <= 3: return 'A', 'AGROPECUÁRIA'
    elif 5 <= div <= 9: return 'B', 'EXTRATIVA'
    elif 10 <= div <= 33: return 'C', 'INDÚSTRIA'
    elif div == 35: return 'D', 'ENERGIA'
    elif 36 <= div <= 39: return 'E', 'SANEAMENTO'
    elif 41 <= div <= 43: return 'F', 'CONSTRUÇÃO'
    elif 45 <= div <= 47: return 'G', 'COMÉRCIO'
    elif 49 <= div <= 53: return 'H', 'TRANSPORTE'
    elif 55 <= div <= 56: return 'I', 'ALIMENTAÇÃO'
    elif 58 <= div <= 63: return 'J', 'INFORMAÇÃO'
    elif 64 <= div <= 66: return 'K', 'FINANÇAS'
    elif div == 68: return 'L', 'IMÓVEIS'
    elif 69 <= div <= 75: return 'M', 'PROFISSIONAL'
    elif 77 <= div <= 82: return 'N', 'ADMINISTRAÇÃO'
    elif div == 84: return 'O', 'PÚBLICO'
    elif div == 85: return 'P', 'EDUCAÇÃO'
    elif 86 <= div <= 88: return 'Q', 'SAÚDE'
    elif 90 <= div <= 93: return 'R', 'CULTURA'
    elif 94 <= div <= 96: return 'S', 'OUTROS'
    elif div == 97: return 'T', 'DOMÉSTICO'
    elif div == 99: return 'U', 'INTERNACIONAL'
    return None, None

cnae[["sigla_secao", "desc_secao"]] = cnae["divisao"].apply(lambda x: pd.Series(mapear_secao(x)))
cnae[["codigo", "descricao", "sigla_secao", "desc_secao"]].to_parquet(os.path.join(gold_path, "dim_cnae.parquet"), index=False)

dim_municipio = pd.read_sql("""
    SELECT DISTINCT e.municipio,
                    m.descricao AS descricao_municipio,
                    e.uf,
                    e.cep
    FROM estabelecimento e
    JOIN municipio m ON e.municipio = m.codigo
    WHERE e.situacao_cadastral = '02'
      AND e.municipio IS NOT NULL
      AND e.uf IS NOT NULL
""", conn)
dim_municipio.to_parquet(os.path.join(gold_path, "dim_municipio.parquet"), index=False)

dim_porte_empresa = pd.DataFrame({
    "porte_empresa": ["00", "01", "03", "05"],
    "descricao_porte_empresa": ["Não Informado", "Micro Empresa", "Empresa de Pequeno Porte", "Demais"]
})
dim_porte_empresa.to_parquet(os.path.join(gold_path, "dim_porte_empresa.parquet"), index=False)

dim_regime = pd.DataFrame({
    "id_regime_tributario": [1, 2, 3],
    "descricao_regime_tributario": ["MEI", "Simples Nacional", "Lucro Presumido / Real"]
})
dim_regime.to_parquet(os.path.join(gold_path, "dim_regime_tributario.parquet"), index=False)

dim_time = time.time() - start
print(f"Tempo para criar as dimensões CNAE e Município e regime tributário e porte_empresa: {dim_time:.2f} segundos")

# === Classificação de Similaridade entre Clientes ===
start = time.time()

print("Carregando CNAEs secundários")
cnae_sec_dict = {}

# Define CNPJs de interesse com base na tabela fato
cnpjs_interesse = set(fato["cnpj"].unique())

# Lê CNAEs secundários somente para os CNPJs de interesse
for chunk in pd.read_sql("SELECT cnpj, cnae_fiscal_secundaria FROM cnae_secundaria", conn, chunksize=100_000):
    chunk = chunk.dropna()
    chunk = chunk[chunk["cnpj"].isin(cnpjs_interesse)]  # filtra aqui
    for row in chunk.itertuples(index=False):
        cnae_sec_dict.setdefault(row.cnpj, set()).add(row.cnae_fiscal_secundaria)

# CNAEs primários da fato
empresa_cnaes = {}
for row in fato[["cnpj", "cnae_fiscal"]].itertuples(index=False):
    if pd.notna(row.cnae_fiscal):
        empresa_cnaes.setdefault(row.cnpj, set()).add(row.cnae_fiscal)

# Junta com os CNAEs secundários
for cnpj, cnaes in cnae_sec_dict.items():
    empresa_cnaes.setdefault(cnpj, set()).update(cnaes)

# Separa clientes reais e potenciais
clientes_reais = set(fato[fato["atual_cliente"] == 1]["cnpj"])
clientes_potenciais = set(fato[fato["atual_cliente"] == 0]["cnpj"])

# Função para encontrar cliente mais similar
def encontrar_cliente_mais_similar(cnpj_potencial):
    cnaes_potencial = empresa_cnaes.get(cnpj_potencial, set())
    if not cnaes_potencial:
        return None, 0.0

    max_sim = 0
    cliente_similar = None
    for cnpj_real in clientes_reais:
        cnaes_real = empresa_cnaes.get(cnpj_real, set())
        if not cnaes_real:
            continue
        inter = len(cnaes_potencial & cnaes_real)
        sim = inter / len(cnaes_real)
        if sim > max_sim:
            max_sim = sim
            cliente_similar = cnpj_real
    return cliente_similar, max_sim

# Aplica a lógica para todos os clientes potenciais
resultados = [
    (cnpj, *encontrar_cliente_mais_similar(cnpj))
    for cnpj in clientes_potenciais
]

df_similaridade = pd.DataFrame(resultados, columns=["cnpj", "cnpj_mais_similar", "similaridade"])

# Junta na fato
fato = fato.merge(df_similaridade, on="cnpj", how="left")

# Salva fato atualizado
fato.to_parquet(os.path.join(gold_path, "fato_empresas.parquet"), index=False)

similaridade_time = time.time() - start
print(f"Tempo para classificar similaridade entre clientes: {similaridade_time:.2f} segundos")

# === Exibir tempos ===
df_tempo = pd.DataFrame([
    ["Bronze - Estabelecimento", bronze_time],
    ["Silver - CNAEs clientes", silver_cnaes_time],
    ["Silver - CNPJs alvo", silver_cnpjs_time],
    ["Gold - fato_empresas", gold_fato_time],
    ["Dimensões finais", dim_time],
    ["Classificação Similaridade Clientes", similaridade_time],
    ["Total", bronze_time + silver_cnaes_time + silver_cnpjs_time + gold_fato_time + dim_time + similaridade_time]
], columns=["Etapa", "Tempo (segundos)"])

print("\n[⏱️] Tempos de execução por etapa:")
print(df_tempo.to_string(index=False))
