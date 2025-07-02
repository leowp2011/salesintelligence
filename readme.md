
Este banco é o ponto de partida para a etapa de transformação.

---

## 2️⃣ Transformation

Este passo executa a geração dos dados analíticos com **Python + Dask + Pandas**.

### 📂 Arquivos esperados em `inputs/`:
- `vendas.csv`: lista de clientes reais com CNPJ
- `leads.csv`: possíveis leads comerciais com CNPJ

### 📜 O script:
- Filtra estabelecimentos ativos (`situacao_cadastral = '02'`)
- Gera os CNAEs utilizados pelos clientes
- Identifica os CNPJs de interesse para análise de mercado
- Realiza joins com dados cadastrais, tributários e de porte
- Cria dimensões: CNAE, Município, Porte da Empresa e Regime Tributário
- Gera arquivos `.parquet` finais na pasta `outputs/gold`

---

### Tabelas geradas (gold):

| Nome do Arquivo                      | Tipo         | Descrição                                                        |
|-------------------------------------|--------------|------------------------------------------------------------------|
| `fato_empresas.parquet`             | Fato         | Empresas ativas com dados enriquecidos e flags (cliente, lead)   |
| `dim_cnae.parquet`                  | Dimensão     | CNAEs com seções e descrições                                    |
| `dim_municipio.parquet`            | Dimensão     | Municípios ativos com nome, UF e CEP                             |
| `dim_porte_empresa.parquet`        | Dimensão     | Tabela de porte com códigos e descrições                         |
| `dim_regime_tributario.parquet`    | Dimensão     | Regime tributário (MEI, Simples, Lucro Real/Presumido)           |

---

## 3️⃣ Visualization (Power BI)

O arquivo Power BI (`.pbip`) está localizado em: