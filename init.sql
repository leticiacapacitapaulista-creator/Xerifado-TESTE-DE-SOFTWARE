CREATE DATABASE IF NOT EXISTS almoxarifado_db;
USE almoxarifado_db;

-- 1. Tabela de Locais (NOVA)
CREATE TABLE IF NOT EXISTS locais (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nome VARCHAR(100) NOT NULL UNIQUE
);

-- 2. Tabela de Usuários
CREATE TABLE IF NOT EXISTS usuarios (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nome VARCHAR(100) NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    telefone VARCHAR(50) DEFAULT NULL,
    senha VARCHAR(255) NOT NULL,
    cargo VARCHAR(50) DEFAULT 'vendedor'
);

-- 3. Tabela de Fornecedores
CREATE TABLE IF NOT EXISTS fornecedores (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nome VARCHAR(100),
    contato_nome VARCHAR(100),
    telefone VARCHAR(50),
    email VARCHAR(100)
);

-- 4. Tabela de Produtos (ATUALIZADA: localizacao agora é local_id)
CREATE TABLE IF NOT EXISTS produtos (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nome VARCHAR(100),
    quantidade INT DEFAULT 0,
    em_falta TINYINT(1) DEFAULT 0,
    local_id INT, -- Mudou de VARCHAR para INT
    estoque_min INT DEFAULT 0,
    fornecedor_id INT,
    gestor_id INT,
    FOREIGN KEY (local_id) REFERENCES locais(id) ON DELETE SET NULL,
    FOREIGN KEY (fornecedor_id) REFERENCES fornecedores(id) ON DELETE SET NULL,
    FOREIGN KEY (gestor_id) REFERENCES usuarios(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS configuracoes (
    chave VARCHAR(50) PRIMARY KEY,
    valor VARCHAR(255) NOT NULL
);

-- Insere o e-mail padrão inicial (se não existir)
INSERT IGNORE INTO configuracoes (chave, valor) VALUES ('email_alerta', 'audemarioestudante@gmail.com');

-- (O resto dos INSERTs de usuários e locais continua igual...)
-- Inserir alguns locais padrão para não começar vazio
INSERT INTO locais (nome) VALUES ('Extradição'), ('generico carga/descarga'), ('generico descarga'), ('generico terminal carga');


-- Inserir um usuário administrador com senha HASH (senha: admin)
INSERT INTO usuarios (nome, email, senha, cargo) 
VALUES ('Admin', 'admin@admin.com', 'scrypt:32768:8:1$J7tSdd2I1tGZzuhn$8ee373f4ac13fa6a5a3cc9a2f5b8685fe46aa120c95cc435e497835f752620662891f42b70f8751fa1e31456481079a861c82e9a0a72f437a429a341a55b3b40', 'admin');