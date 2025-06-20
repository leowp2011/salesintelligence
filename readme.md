# Análise de Mercado por CNAE

Este projeto tem como objetivo analisar o mercado brasileiro com base nos dados públicos da Receita Federal, utilizando o CNAE para segmentação e geração de KPIs que suportam decisões estratégicas.

---

## 1. Extract & Load

Utilizamos o repositório [rictom/cnpj-sqlite](https://github.com/rictom/cnpj-sqlite) para:

- Download e descompactação automatizada dos arquivos públicos da Receita Federal;
- Importação dos dados para banco SQLite;
- Geração do banco `.db` completo com todas as tabelas do CNPJ.

Esta etapa prepara a base bruta para as transformações.

![Relacionamentos](images/1-relacionamentos.png)

---

## 2. Transformation

Nesta etapa, os dados são preparados para análise no Power BI, melhorando a performance e a qualidade das informações.

**Pré-requisito:** A tabela `cnpj_input` deve conter os CNPJs dos clientes da empresa para limitar o escopo da análise aos CNAEs de interesse.

| Script                                 | KPI Relacionado                          | Tabela Gerada                | Descrição Rápida                                          |
|---------------------------------------|----------------------------------------|-----------------------------|----------------------------------------------------------|
| `01_selecionar_empresas_ativas.sql`      | Total de empresas ativas por CNAE        | `d_empresas_ativas`           | Dimensão de empresas ativas filtradas para análise       |
| `02_filtrar_estabelecimentos_validos.sql`| Quantidade de clientes ativos por CNAE    | `d_estabelecimentos_validos`  | Estabelecimentos válidos vinculados às empresas           |
| `03_integrar_clientes_detalhados.sql`     | Base para taxa de atendimento do mercado  | `f_clientes_detalhados`       | Integra clientes com dados cadastrais detalhados          |
| `04_calcular_taxa_atendimento_cnae.sql`   | Taxa de atendimento do mercado por CNAE   | `f_taxa_atendimento_cnae`     | Calcula a taxa de atendimento por CNAE                     |
| `05_analise_receita_regional.sql`          | Receita e padrões de consumo regional     | `f_receita_regional_produto`  | Receita e volume por produto e região                      |
| `06_simular_potencial_receita.sql`         | Potencial de receita regional por produto | `f_potencial_receita_simulada`| Estimativa de receita incremental por cenário de mercado  |

---

## 3. Visualização e Análise

Os dados gerados nas etapas anteriores são consumidos no Power BI para criação dos dashboards e análises de mercado.

---


## 🛠️ Tecnologias Utilizadas

- **GitHub**  
  Plataforma para versionamento de código e hospedagem do repositório com os scripts e documentação do projeto.

- **Python**  
  Linguagem utilizada para automatizar o download, descompactação e pré-processamento dos dados públicos da Receita Federal.

- **SQLite**  
  Banco de dados leve utilizado para armazenar, tratar e consultar os dados extraídos da Receita Federal.

- **DBeaver**  
  Ferramenta gráfica para gerenciar e executar consultas SQL no banco SQLite, facilitando o desenvolvimento e análise.

- **Visual Studio Code**  
  Editor de código usado para desenvolver os scripts Python e SQL com suporte a plugins e integração.

- **Power BI**  
  Plataforma de Business Intelligence para criação de dashboards interativos e análise visual dos KPIs extraídos.

