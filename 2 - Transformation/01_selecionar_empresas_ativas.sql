-- Remove a tabela se já existir
DROP TABLE IF EXISTS f_base_clientes;

-- Cria a tabela fato inicial com a coluna cnpj_basico
CREATE TABLE f_base_clientes (
    cnpj_basico TEXT PRIMARY KEY
);

-- Insere os CNPJs básicos filtrados conforme sua regra
INSERT INTO f_base_clientes (cnpj_basico)
SELECT DISTINCT ci.cnpj_basico 
FROM cnpj_input ci 
JOIN estabelecimento t ON ci.cnpj_basico = t.cnpj_basico 
JOIN empresas te ON te.cnpj_basico = t.cnpj_basico
JOIN simples tsim ON tsim.cnpj_basico = te.cnpj_basico
WHERE t.motivo_situacao_cadastral = '00'
  AND tsim.opcao_simples = 'N'
  AND tsim.opcao_mei = 'N';
