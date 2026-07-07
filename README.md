## INSTITUTO FEDERAL DE PERNAMBUCO - CAMPUS PAULISTA

### 🎓 Informações Acadêmicas

#### CURSO: ADS -  TESTE DE SOFTWARE

#### ALUNO: LETICIA RENATA;

#### GIT'S: leticiacapacitapaulista-creator; 

Projeto desenvolvido para a matéria de Desenvolvimento web II

---

## 📝 Sistema de Gerenciamento de Almoxarifado - Xerifado

Este é um sistema web desenvolvido para o controle, monitoramento e gerenciamento de insumos e produtos de um Almoxarifado. O sistema conta com controle de níveis de acesso por cargos (Administrador, Gestor e Vendedor), cálculo automático de estoque baixo e envio automatizado de alertas de reabastecimento.

O ambiente e o banco de dados são gerenciados usando o Docker, enquanto a suíte de testes de integração é executada na sua máquina local, comunicando-se diretamente com o banco de dados ativo no container.

---

## 🚀 Tecnologias Utilizadas

Python 3.14 — Linguagem base do ecossistema.

Flask 1.3.0 — Micro-framework web para construção das rotas e lógica do servidor.

MySQL — Banco de dados relacional para armazenamento de usuários, produtos e movimentações.

Docker Desktop — Criação e isolamento do container de banco de dados.

Pytest 9.1.0 — Framework utilizado para a automação e execução da suíte de testes de integração.

---

## 🛠️ Como Iniciar o Projeto (Docker Desktop)

Siga o passo a passo abaixo para subir o banco de dados MySQL no Docker do seu computador:
Abra o Docker Desktop no seu computador.

Suba o container do banco de dados:
Abra o terminal do seu Windows (PowerShell ou CMD) na raiz do projeto e execute:

```bash
### docker compose up -d
```

Verifique se o banco está ativo, Você pode conferir pelo painel visual do Docker Desktop ou pelo comando:

### docker compose ps

---

## ⚙️ Configuração para os Testes Unitários e de Integração

Foram desenvolvidos testes automatizados utilizando o framework **Pytest**, com o objetivo de validar rotas e comportamentos da aplicação.

Como os testes rodam diretamente no terminal do seu Windows, o Python precisa saber que o MySQL está acessível através do endereço local do seu próprio computador.

Antes de rodar os testes, certifique-se de que a linha de configuração do Host no seu app.py está definida para usar o IP 127.0.0.1 como padrão quando executada fora do container:

Python

###### app.config['MYSQL_HOST'] = os.environ.get('MYSQL_HOST', '127.0.0.1')

#### O link que será gerado do Docker sobre o projeto é: http://localhost:8000/login

---

## 📦Suíte de Testes Automatizados (Pytest)

Com o banco de dados ativo no Docker, você pode rodar os comandos abaixo diretamente no terminal do seu Windows (PS C:\Users\...). Os testes vão ler, gravar e validar as regras de negócio usando dados reais dentro do MySQL.

## 🌟 Comando para rodar TODOS os testes do projeto de uma vez:

### pytest testes/ -v -s

##### OBS: EMERGÊNCIA PARA CASO O VENV NÃO FUNCIONAR CORRETAMENTE:
deactivate                       
>> Remove-Item -Recurse -Force .venv
>> python -m venv .venv
>> .\.venv\Scripts\Activate.ps1
>> python -m pip install -r requirements.txt
>> python -m pip install pytest

--- 

## 📦 Comandos de Testes por Arquivo e Isolados

**Se preferir validar seções específicas do projeto separadamente, utilize os comandos abaixo.**

### 1 - Autenticação e Segurança (test_login.py)

Valida o comportamento das rotas de login, renderização de templates HTML e as telas de recuperação/reset de senha integradas ao banco.

**Comando Geral do arquivo:**

### pytest testes/test_login.py -v -s

---

**Comando Separado por Função:**

### CT01 - Acesso à página de Login (Verifica se a página retorna HTML válido (Status 200))
pytest testes/test_login.py::test_login_contem_html -v -s

### CT02 - Verifica exibição do formulário "Esqueci a Senha"
pytest testes/test_login.py::test_esqueci_senha_exibe_formulario -v -s

### CT03 - Verifica o fluxo de solicitação de reset de senha
pytest testes/test_login.py::test_solicitar_reset_senha_retorna_mensagem -v -s

### CT04 - Valida tentativa de login com credenciais incorretas no banco
pytest testes/test_login.py::test_login_credenciais_invalidas -v -s

---

## 2. Níveis de Acesso e Cargos (test_permissoes_usuarios.py)
Garante que as regras de privilégios entre Administradores, Gestores e Vendedores sejam respeitadas rigorosamente no sistema.

Comando Geral do arquivo:

### pytest testes/test_permissoes_usuarios.py -v -s

---

Comando Separado por Função:

### CT05 - Valida bloqueio ao tentar remover usuários administradores
pytest testes/test_permissoes_usuarios.py::test_mensagem_permissao_remocao_usuario_bloqueia_gestor_para_admin -v -s

### CT06 - Valida a lógica de quem possui permissão para editar perfis
pytest testes/test_permissoes_usuarios.py::test_pode_editar_usuario_restringe_gestor_para_admin -v -s

---

## 3. Regras de Negócio do Estoque (test_regras_estoque.py)
Testa as funções matemáticas que controlam o estoque mínimo de segurança e a listagem de itens críticos.

Comando Geral do arquivo:

### pytest testes/test_regras_estoque.py -v -s

---

Comando Separado por Função:

### CT07 - Valida gatilho quando o estoque atinge o nível mínimo
pytest testes/test_regras_estoque.py::test_estoque_baixo_conta_quando_atinge_o_minimo -v -s

### CT08 - Garante filtragem correta apenas de itens com quantidades críticas
pytest testes/test_regras_estoque.py::test_get_itens_estoque_baixo_retorna_apenas_itens_abaixo_do_minimo -v -s

### CT09 - Valida inclusão de produtos marcados manualmente como "em falta"
pytest testes/test_regras_estoque.py::test_get_itens_estoque_baixo_inclui_itens_solicitados_em_falta -v -s

---

## 4. Endpoints e Rotas HTTP (test_rotas_http.py)
Valida os códigos de resposta HTTP diretos gerados pelo servidor web do Flask.

Comando Geral do arquivo:

### pytest testes/test_rotas_http.py -v -s

---

*Comando Separado por Função / Filtro:*

### CT10 - Garante o retorno do erro padrão 404 para links inválidos
pytest testes/test_rotas_http.py -k "rota_inexistente" -v -s

---

## 5. Banco de Dados e Consultas (test_banco_mocks.py)
Valida o comportamento das funções que interagem com e-mails de alerta e formatação de logs de auditoria históricos.

Comando Geral do arquivo:

### pytest testes/test_banco_mocks.py -v -s

--- 

Comando Separado por Função:

### CT11 - Valida tratamento de dicionários para destinatários de alertas gerais
pytest testes/test_banco_mocks.py::test_obter_destinatarios_alerta_aceita_cursor_com_dicionarios -v -s

### CT12 - Valida emails de alerta focados em reabastecimento para os cargos responsáveis
pytest testes/test_banco_mocks.py::test_obter_destinatarios_alerta_reabastecimento_inclui_gestor_e_vendedor -v -s

### CT13 - Testa a gravação da estrutura do histórico de movimentações (Log)
pytest testes/test_banco_mocks.py::test_registrar_movimentacao_cria_registro_com_tipo_e_usuario -v -s

### CT14 - Garante o filtro correto separando o tipo "reabastecimento" no histórico
pytest testes/test_banco_mocks.py::test_get_alertas_reabastecimento_filtra_registros_reabastecimento -v -s

---

📌 Considerações Finais

A aplicação dos testes automatizados permite validar o funcionamento do sistema de almoxarifado, reduzindo erros e aumentando a confiabilidade do software.

O projeto demonstra a importância da etapa de testes no ciclo de desenvolvimento de software, garantindo maior qualidade e segurança na entrega da aplicação.
