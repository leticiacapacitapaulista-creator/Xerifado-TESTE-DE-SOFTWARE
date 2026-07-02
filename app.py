from flask import Flask, render_template, request, redirect, url_for, jsonify, make_response, session
import mysql.connector as driver
import os
import requests
import threading
import random
import time
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from flask_jwt_extended import (
    JWTManager, create_access_token, jwt_required, 
    get_jwt_identity, get_jwt, set_access_cookies, 
    unset_jwt_cookies
)
from functools import wraps
from flask_caching import Cache

app = Flask(__name__)

# --- CONFIGURAÇÃO ---
app.secret_key = 'sua_chave_secreta_flask'
app.config['MYSQL_HOST'] = os.environ.get('MYSQL_HOST', '127.0.0.1')
app.config['MYSQL_USER'] = os.environ.get('MYSQL_USER', 'root')
app.config['MYSQL_PASSWORD'] = os.environ.get('MYSQL_ROOT_PASSWORD', 'admin123')
app.config['MYSQL_DATABASE'] = os.environ.get('MYSQL_DATABASE', 'almoxarifado_db')
app.config['SECRET_KEY'] = 'sua_chave_secreta_flask'
#jwt
app.config['JWT_SECRET_KEY'] = 'sua_chave_jwt_super_secreta' 
app.config['JWT_TOKEN_LOCATION'] = ['cookies']
app.config['JWT_COOKIE_CSRF_PROTECT'] = False 
jwt = JWTManager(app)
#cache
app.config['CACHE_TYPE'] = 'FileSystemCache'
app.config['CACHE_DIR'] = '/tmp/flask_cache' # Pasta temporária do Linux
app.config['CACHE_DEFAULT_TIMEOUT'] = 300 # 5 minutos
app.config['CACHE_THRESHOLD'] = 500 

cache = Cache(app)

historico_memoria = []
historico_seq = 0

# --- TRATAMENTO DE ERROS JWT ---
@jwt.unauthorized_loader
def missing_token_callback(error_string): return redirect(url_for('login'))
@jwt.expired_token_loader
def expired_token_callback(jwt_header, jwt_payload): return redirect(url_for('login'))
@jwt.invalid_token_loader
def invalid_token_callback(error_string): return redirect(url_for('login'))

# --- ADAPTER MYSQL ---
class MySQLAdapter:
    def __init__(self, app): self.app = app
    @property
    def connection(self):
        return driver.connect(
            host=self.app.config['MYSQL_HOST'], 
            user=self.app.config['MYSQL_USER'], 
            password=self.app.config['MYSQL_PASSWORD'], 
            database=self.app.config['MYSQL_DATABASE']
        )

mysql = MySQLAdapter(app)


def garantir_coluna_telefone():
    try:
        conn = mysql.connection
        cursor = conn.cursor()
        cursor.execute("USE almoxarifado_db")
        cursor.execute("SHOW COLUMNS FROM usuarios LIKE 'telefone'")
        if cursor.fetchone() is None:
            cursor.execute("ALTER TABLE usuarios ADD COLUMN telefone VARCHAR(50) DEFAULT NULL")
            conn.commit()
        cursor.close(); conn.close()
    except Exception as e:
        print(f"Falha ao garantir coluna telefone: {e}")


def garantir_coluna_em_falta():
    try:
        conn = mysql.connection
        cursor = conn.cursor()
        cursor.execute("USE almoxarifado_db")
        cursor.execute("SHOW COLUMNS FROM produtos LIKE 'em_falta'")
        if cursor.fetchone() is None:
            cursor.execute("ALTER TABLE produtos ADD COLUMN em_falta TINYINT(1) DEFAULT 0")
            conn.commit()
        cursor.close(); conn.close()
    except Exception as e:
        print(f"Falha ao garantir coluna em_falta: {e}")


def garantir_tabela_historico_movimentacoes():
    try:
        conn = mysql.connection
        cursor = conn.cursor()
        cursor.execute("USE almoxarifado_db")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS historico_movimentacoes (
                id INT AUTO_INCREMENT PRIMARY KEY,
                produto_id INT,
                produto_nome VARCHAR(255),
                tipo VARCHAR(50) NOT NULL,
                descricao TEXT,
                usuario_id INT,
                usuario_nome VARCHAR(255),
                usuario_cargo VARCHAR(50),
                local_origem VARCHAR(255),
                local_destino VARCHAR(255),
                quantidade_anterior INT,
                quantidade_nova INT,
                criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
        cursor.close(); conn.close()
    except Exception as e:
        print(f"Falha ao garantir tabela historico_movimentacoes: {e}")


def get_usuario_logado():
    try:
        claims = get_jwt()
        user_id = get_jwt_identity()
        return {
            'id': user_id,
            'nome': claims.get('nome'),
            'cargo': claims.get('cargo')
        }
    except Exception:
        return None


def registrar_movimentacao(produto_id, produto_nome, tipo, descricao, usuario_id=None, usuario_nome=None, usuario_cargo=None, local_origem=None, local_destino=None, quantidade_anterior=None, quantidade_nova=None):
    global historico_seq, historico_memoria
    try:
        usuario = get_usuario_logado() if usuario_id is None and usuario_nome is None and usuario_cargo is None else None
        if usuario is not None:
            usuario_id = usuario_id if usuario_id is not None else usuario.get('id')
            usuario_nome = usuario_nome if usuario_nome is not None else usuario.get('nome')
            usuario_cargo = usuario_cargo if usuario_cargo is not None else usuario.get('cargo')

        conn = mysql.connection
        cursor = conn.cursor()
        cursor.execute("USE almoxarifado_db")
        cursor.execute("""
            INSERT INTO historico_movimentacoes (
                produto_id, produto_nome, tipo, descricao, usuario_id, usuario_nome, usuario_cargo,
                local_origem, local_destino, quantidade_anterior, quantidade_nova
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            produto_id,
            produto_nome,
            tipo,
            descricao,
            usuario_id,
            usuario_nome,
            usuario_cargo,
            local_origem,
            local_destino,
            quantidade_anterior,
            quantidade_nova,
        ))
        conn.commit()
        registro_id = cursor.lastrowid
        cursor.close(); conn.close()
        return registro_id
    except Exception as e:
        print(f"Falha ao registrar movimentação: {e}")
        historico_seq += 1
        historico_memoria.append({
            'id': historico_seq,
            'produto_id': produto_id,
            'produto_nome': produto_nome,
            'tipo': tipo,
            'descricao': descricao,
            'usuario_id': usuario_id,
            'usuario_nome': usuario_nome,
            'usuario_cargo': usuario_cargo,
            'local_origem': local_origem,
            'local_destino': local_destino,
            'quantidade_anterior': quantidade_anterior,
            'quantidade_nova': quantidade_nova,
            'criado_em': datetime.now(),
        })
        return historico_seq


garantir_coluna_telefone()
garantir_coluna_em_falta()
garantir_tabela_historico_movimentacoes()

# --- DECORATOR DE PERMISSÃO ---
def role_required(roles_permitidas):
    def wrapper(fn):
        @wraps(fn)
        @jwt_required()
        def decorator(*args, **kwargs):
            claims = get_jwt()
            if claims.get('cargo') not in roles_permitidas:
                return jsonify({"msg": "Acesso negado"}), 403
            return fn(*args, **kwargs)
        return decorator
    return wrapper

# --- UTILITÁRIOS (EMAILS) ---
def chamar_microservico_email(subject, body, to_email=None):
    try:
        payload = {'subject': subject, 'body': body}
        if to_email:
            payload['to_email'] = to_email
        requests.post('http://email_service:5001/send_email', json=payload, timeout=2)
    except Exception as e:
        print(f"Falha ao chamar microserviço de e-mail: {e}")

def enviar_boas_vindas_thread(nome, email, senha_raw):
    subject = "Bem-vindo ao Sistema de Almoxarifado - Credenciais"
    body = f"""Olá {nome},
Sua conta foi criada com sucesso.
Login: {email}
Senha: {senha_raw}
Por favor, altere sua senha após o primeiro acesso."""
    chamar_microservico_email(subject, body, to_email=email)

def is_estoque_baixo(quantidade, estoque_min, em_falta=False):
    try:
        qtd = int(quantidade) if quantidade is not None else 0
        minimo = int(estoque_min) if estoque_min is not None else 0
    except (TypeError, ValueError):
        return False
    return em_falta or qtd <= minimo


def deve_alertar_reabastecimento(quantidade_anterior, quantidade_nova):
    try:
        antiga = int(quantidade_anterior) if quantidade_anterior is not None else 0
        nova = int(quantidade_nova) if quantidade_nova is not None else 0
    except (TypeError, ValueError):
        return False
    return nova > antiga


def get_alertas_reabastecimento(cursor, fallback=None, limit=10):
    try:
        cursor.execute("""
            SELECT * FROM historico_movimentacoes
            WHERE tipo = 'reabastecimento'
            ORDER BY criado_em DESC, id DESC
            LIMIT %s
        """, (limit,))
        registros = cursor.fetchall()
        if not registros:
            return []
        return [item for item in registros if item.get('tipo') == 'reabastecimento'] if isinstance(registros[0], dict) else registros
    except Exception:
        if fallback is None:
            return []
        return [item for item in fallback if item.get('tipo') == 'reabastecimento'][-limit:]


def get_itens_estoque_baixo(produtos):
    return [produto for produto in produtos if is_estoque_baixo(produto.get('quantidade'), produto.get('estoque_min'), produto.get('em_falta'))]


def mensagem_permissao_remocao_usuario(cargo_usuario_logado, cargo_usuario_alvo):
    if cargo_usuario_logado == 'admin':
        return None
    if cargo_usuario_alvo == 'admin':
        return 'Você não tem permissão para remover usuários administradores.'
    return 'Você não tem permissão para remover usuários.'


def pode_editar_usuario(cargo_usuario_logado, cargo_usuario_alvo):
    if cargo_usuario_logado == 'admin':
        return True
    if cargo_usuario_alvo == 'admin':
        return False
    return True


def obter_destinatarios_alerta(cursor):
    emails = []

    def extrair_emails(row):
        if not row:
            return []
        if isinstance(row, dict):
            email = row.get('valor') or row.get('email')
            return [email] if email else []
        if isinstance(row, (list, tuple)):
            valores = []
            for item in row:
                valores.extend(extrair_emails(item))
            return valores
        return [row] if row else []

    cursor.execute("SELECT valor FROM configuracoes WHERE chave = 'email_alerta'")
    res = cursor.fetchone()
    for email in extrair_emails(res):
        if email and email not in emails:
            emails.append(email)

    cursor.execute("SELECT email FROM usuarios WHERE cargo IN ('admin', 'gestor') AND email IS NOT NULL AND email != ''")
    for row in cursor.fetchall():
        for email in extrair_emails(row):
            if email and email not in emails:
                emails.append(email)
    return emails


def obter_destinatarios_alerta_reabastecimento(cursor):
    emails = []

    def extrair_emails(row):
        if not row:
            return []
        if isinstance(row, dict):
            email = row.get('valor') or row.get('email')
            return [email] if email else []
        if isinstance(row, (list, tuple)):
            valores = []
            for item in row:
                valores.extend(extrair_emails(item))
            return valores
        return [row] if row else []

    cursor.execute("SELECT valor FROM configuracoes WHERE chave = 'email_alerta'")
    res = cursor.fetchone()
    for email in extrair_emails(res):
        if email and email not in emails:
            emails.append(email)

    cursor.execute("SELECT email FROM usuarios WHERE cargo IN ('admin', 'gestor', 'vendedor') AND email IS NOT NULL AND email != ''")
    for row in cursor.fetchall():
        for email in extrair_emails(row):
            if email and email not in emails:
                emails.append(email)
    return emails


def disparar_alerta_estoque_baixo(pid, nome, destinatarios):
    subject = f"ALERTA: Estoque Baixo (Item {pid})"
    body = f"O produto '{nome}' atingiu o nível mínimo de estoque."
    if isinstance(destinatarios, (list, tuple, set)):
        emails = [d for d in destinatarios if d]
    elif destinatarios:
        emails = [destinatarios]
    else:
        emails = []

    for email in emails:
        threading.Thread(target=chamar_microservico_email, args=[subject, body, email]).start()


def disparar_alerta_reabastecimento(pid, nome, quantidade_anterior, quantidade_nova, destinatarios):
    subject = f"Reabastecimento realizado: {nome}"
    body = f"O produto '{nome}' foi reabastecido de {quantidade_anterior} para {quantidade_nova} unidade(s)."
    if isinstance(destinatarios, (list, tuple, set)):
        emails = [d for d in destinatarios if d]
    elif destinatarios:
        emails = [destinatarios]
    else:
        emails = []

    for email in emails:
        threading.Thread(target=chamar_microservico_email, args=[subject, body, email]).start()


def normalizar_tab_ativo(cargo_usuario, tab_solicitada):
    if cargo_usuario == 'vendedor':
        if tab_solicitada in ['reabastecimentos', 'reabastecimento']:
            return 'reabastecimentos'
        return 'produtos'
    return tab_solicitada or 'dashboard'


def calcular_quantidade_final(quantidade_atual, quantidade_nova):
    try:
        atual = int(quantidade_atual) if quantidade_atual is not None else 0
        nova = int(quantidade_nova) if quantidade_nova is not None else 0
    except (TypeError, ValueError):
        return quantidade_atual if quantidade_atual is not None else 0
    return atual + nova


def contar_alertas_reabastecimento(alertas):
    return len(alertas or [])


def gerar_codigo_reset():
    return str(random.randint(100000, 999999))


def enviar_codigo_sms(telefone, codigo):
    if not telefone:
        return False
    print(f"[SMS SIMULADO] Enviando código {codigo} para {telefone}")
    return True

# --- DADOS COMUNS (COM LOCAIS) ---
def get_dados_comuns():
    conn = mysql.connection
    cursor = conn.cursor(dictionary=True)
    cursor.execute("USE almoxarifado_db")
    
    cursor.execute("SELECT SUM(quantidade) as total FROM produtos")
    res = cursor.fetchone()
    total_itens = res['total'] if res and res['total'] else 0
   
    cursor.execute("SELECT COUNT(id) as count FROM produtos WHERE quantidade <= estoque_min OR em_falta = 1")
    res = cursor.fetchone()
    estoque_baixo_count = res['count'] if res else 0
    
    cursor.execute("""
        SELECT p.*, f.nome as fornecedor_nome, u.nome as gestor_nome, l.nome as local_nome
        FROM produtos p
        LEFT JOIN fornecedores f ON p.fornecedor_id = f.id
        LEFT JOIN usuarios u ON p.gestor_id = u.id
        LEFT JOIN locais l ON p.local_id = l.id
        ORDER BY p.nome
    """)
    produtos = cursor.fetchall()
    
    cursor.execute("SELECT * FROM fornecedores ORDER BY nome")
    fornecedores = cursor.fetchall()
    
    cursor.execute("SELECT * FROM locais ORDER BY nome")
    locais = cursor.fetchall()
    
    cursor.execute("SELECT id, nome, email, cargo FROM usuarios ORDER BY nome")
    usuarios = cursor.fetchall()
   
    cursor.close()
    conn.close()
   
    return {
        'total_itens': total_itens,
        'estoque_baixo_count': estoque_baixo_count,
        'produtos': produtos,
        'fornecedores': fornecedores,
        'locais': locais,
        'usuarios': usuarios  
    }

# --- FUNÇÃO CACHE
@cache.cached(timeout=300, key_prefix='dados_dashboard')
def get_dados_comuns_cache():
    """
    Esta função verifica se já existe o resultado salvo no arquivo.
    Se existir, retorna o arquivo (rápido).
    Se não, roda a get_dados_comuns(), salva no arquivo e retorna.
    """
    return get_dados_comuns()

# --- ROTAS DE AUTENTICAÇÃO ---
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET': return render_template('login.html')
    email = request.form.get('email')
    password = request.form.get('password')
    
    conn = mysql.connection
    cursor = conn.cursor(dictionary=True)
    cursor.execute("USE almoxarifado_db")
    cursor.execute("SELECT * FROM usuarios WHERE email = %s", (email,))
    user = cursor.fetchone()
    cursor.close()
    conn.close()

    if user and check_password_hash(user['senha'], password):
        token = create_access_token(identity=str(user['id']), additional_claims={"cargo": user['cargo'], "nome": user['nome']})
        resp = make_response(redirect(url_for('index')))
        set_access_cookies(resp, token)
        return resp
    return render_template('login.html', erro="Credenciais Inválidas")

@app.route('/esqueci_senha', methods=['GET', 'POST'])
def esqueci_senha():
    if request.method == 'GET':
        return render_template('esqueci_senha.html')

    email = request.form.get('email', '').strip()
    codigo = request.form.get('codigo', '').strip()
    nova_senha = request.form.get('senha', '').strip()

    if codigo and nova_senha:
        if session.get('reset_email') != email:
            return render_template('esqueci_senha.html', mensagem='E-mail inválido para redefinição.', etapa='codigo', email=email)

        codigo_esperado = session.get('reset_codigo')
        codigo_expira_em = session.get('reset_codigo_expira', 0)
        if not codigo_esperado or codigo != codigo_esperado or time.time() > codigo_expira_em:
            return render_template('esqueci_senha.html', mensagem='Código inválido ou expirado. Solicite um novo.', etapa='codigo', email=email)

        try:
            conn = mysql.connection
            cursor = conn.cursor()
            cursor.execute("USE almoxarifado_db")
            cursor.execute("UPDATE usuarios SET senha = %s WHERE email = %s", (generate_password_hash(nova_senha), email))
            conn.commit()
        except Exception as e:
            print(f"Erro ao redefinir senha: {e}")
            return render_template('esqueci_senha.html', mensagem='Não foi possível redefinir a senha no momento.', etapa='codigo', email=email)
        finally:
            try:
                cursor.close(); conn.close()
            except Exception:
                pass

        session.pop('reset_email', None)
        session.pop('reset_codigo', None)
        session.pop('reset_codigo_expira', None)
        session.pop('reset_user_id', None)
        session.pop('reset_phone', None)
        return render_template('esqueci_senha.html', mensagem='Senha redefinida com sucesso. Você já pode entrar no sistema.', sucesso=True)

    if not email:
        return render_template('esqueci_senha.html', mensagem='Informe o e-mail cadastrado.')

    try:
        conn = mysql.connection
        cursor = conn.cursor(dictionary=True)
        cursor.execute("USE almoxarifado_db")
        cursor.execute("SELECT id, email, telefone FROM usuarios WHERE email = %s", (email,))
        usuario = cursor.fetchone()
    except Exception as e:
        print(f"Erro ao buscar usuário para reset: {e}")
        usuario = None
    finally:
        try:
            cursor.close(); conn.close()
        except Exception:
            pass

    if usuario:
        codigo = gerar_codigo_reset()
        session['reset_email'] = usuario['email']
        session['reset_user_id'] = usuario['id']
        session['reset_phone'] = usuario.get('telefone')
        session['reset_codigo'] = codigo
        session['reset_codigo_expira'] = int(time.time()) + 600
        enviar_codigo_sms(usuario.get('telefone'), codigo)
        return render_template('esqueci_senha.html', mensagem=f'Enviamos um código para o telefone cadastrado ({usuario.get("telefone") or "não informado"}).', etapa='codigo', email=usuario['email'], telefone=usuario.get('telefone'))

    return render_template('esqueci_senha.html', mensagem='Se o e-mail estiver cadastrado, enviaremos um código para o telefone registrado.')


@app.route('/logout')
def logout():
    resp = make_response(redirect(url_for('login')))
    unset_jwt_cookies(resp)
    return resp

@app.route('/minha_conta', methods=['POST'])
@jwt_required()
def minha_conta():
    usuario_id = get_jwt_identity()
    nova_senha = request.form.get('senha')
    novo_email = request.form.get('email')
    novo_telefone = request.form.get('telefone')
    conn = mysql.connection
    cursor = conn.cursor()
    cursor.execute("USE almoxarifado_db")
    try:
        if novo_email: cursor.execute("UPDATE usuarios SET email = %s WHERE id = %s", (novo_email, usuario_id))
        if novo_telefone is not None: cursor.execute("UPDATE usuarios SET telefone = %s WHERE id = %s", (novo_telefone or None, usuario_id))
        if nova_senha and nova_senha.strip():
            sh = generate_password_hash(nova_senha)
            cursor.execute("UPDATE usuarios SET senha = %s WHERE id = %s", (sh, usuario_id))
        conn.commit()
        cache.delete('dados_dashboard')
    except: pass
    cursor.close()
    conn.close()
    return redirect(url_for('index'))

# --- ROTA PRINCIPAL (INDEX) ---
@app.route('/')
@jwt_required()
def index():
    claims = get_jwt()
    user_cargo = claims.get('cargo', 'vendedor')
    
    # Lógica de Abas
    active_tab = normalizar_tab_ativo(user_cargo, request.args.get('tab'))
    if user_cargo not in ['admin', 'gestor'] and active_tab == 'usuarios':
        active_tab = 'produtos' if user_cargo == 'vendedor' else 'dashboard'

    # Lógica de Edição
    edit_produto_id = request.args.get('edit_produto')
    edit_fornecedor_id = request.args.get('edit_fornecedor')
    edit_local_id = request.args.get('edit_local')
    edit_usuario_id = request.args.get('edit_usuario')
    erro_msg = request.args.get('erro_msg')
    
    produto_para_editar = None
    fornecedor_para_editar = None
    local_para_editar = None
    usuario_para_editar = None
    email_alerta_atual = ""

    conn = mysql.connection
    cursor = conn.cursor(dictionary=True)
    cursor.execute("USE almoxarifado_db")
    
    # Buscas pontuais (Edição não usa cache pois precisa ser imediato)
    if edit_produto_id:
        cursor.execute("SELECT * FROM produtos WHERE id = %s", (edit_produto_id,))
        produto_para_editar = cursor.fetchone()
        active_tab = 'dashboard'
    
    if edit_fornecedor_id and user_cargo in ['admin', 'gestor']:
        cursor.execute("SELECT * FROM fornecedores WHERE id = %s", (edit_fornecedor_id,))
        fornecedor_para_editar = cursor.fetchone()
        active_tab = 'fornecedores'

    if edit_local_id and user_cargo in ['admin', 'gestor']:
        cursor.execute("SELECT * FROM locais WHERE id = %s", (edit_local_id,))
        local_para_editar = cursor.fetchone()
        active_tab = 'locais'
        
    if edit_usuario_id and user_cargo == 'admin':
        cursor.execute("SELECT * FROM usuarios WHERE id = %s", (edit_usuario_id,))
        usuario_para_editar = cursor.fetchone()
        active_tab = 'usuarios'

    historico_movimentacoes = []
    alertas_reabastecimento = []
    if user_cargo in ['admin', 'gestor']:
        cursor.execute("SELECT valor FROM configuracoes WHERE chave = 'email_alerta'")
        res = cursor.fetchone()
        if res: email_alerta_atual = res['valor']

        try:
            cursor.execute("""
                SELECT * FROM historico_movimentacoes
                ORDER BY criado_em DESC, id DESC
                LIMIT 200
            """)
            historico_movimentacoes = cursor.fetchall()
        except Exception:
            historico_movimentacoes = list(reversed(historico_memoria))

    if user_cargo in ['vendedor', 'gestor']:
        try:
            alertas_reabastecimento = get_alertas_reabastecimento(cursor, fallback=historico_memoria, limit=10)
        except Exception:
            alertas_reabastecimento = []

    cursor.close()
    conn.close()

    # Chamamos a versão cacheada. Se o cache existir, nem bate no banco.
    dados = get_dados_comuns_cache()
    contador_alertas_reabastecimento = contar_alertas_reabastecimento(alertas_reabastecimento)
    itens_estoque_baixo = get_itens_estoque_baixo(dados.get('produtos', []))
    
    return render_template('almoxarifado_dashboard.html', 
                           active_tab=active_tab, 
                           produto_para_editar=produto_para_editar, 
                           fornecedor_para_editar=fornecedor_para_editar,
                           local_para_editar=local_para_editar,
                           usuario_para_editar=usuario_para_editar, 
                           current_user_role=user_cargo,
                           config_email_alerta=email_alerta_atual,
                           erro_msg=erro_msg,
                           itens_estoque_baixo=itens_estoque_baixo,
                           historico_movimentacoes=historico_movimentacoes,
                           alertas_reabastecimento=alertas_reabastecimento,
                           contador_alertas_reabastecimento=contador_alertas_reabastecimento,
                           **dados)

# --- ROTAS DE CONFIGURAÇÃO ---
@app.route('/config/atualizar_email', methods=['POST'])
@role_required(['admin'])
def atualizar_email_alerta():
    novo_email = request.form.get('email_alerta')
    conn = mysql.connection
    cursor = conn.cursor()
    cursor.execute("USE almoxarifado_db")
    try:
        cursor.execute("REPLACE INTO configuracoes (chave, valor) VALUES ('email_alerta', %s)", (novo_email,))
        conn.commit()
        cache.delete('dados_dashboard')
    except Exception as e: print(f"Erro config: {e}")
    finally: cursor.close(); conn.close()
    return redirect(url_for('index', tab='usuarios'))

# --- ROTAS DE LOCAIS ---
@app.route('/locais/adicionar', methods=['POST'])
@role_required(['admin', 'gestor'])
def adicionar_local():
    conn = mysql.connection; cursor = conn.cursor(); cursor.execute("USE almoxarifado_db")
    try:
        cursor.execute("INSERT INTO locais (nome) VALUES (%s)", (request.form.get('nome'),))
        conn.commit()

        cache.delete('dados_dashboard')
    except: pass
    cursor.close(); conn.close()
    return redirect(url_for('index', tab='locais'))

@app.route('/locais/editar/<int:local_id>', methods=['POST'])
@role_required(['admin', 'gestor'])
def editar_local(local_id):
    conn = mysql.connection; cursor = conn.cursor(); cursor.execute("USE almoxarifado_db")
    cursor.execute("UPDATE locais SET nome=%s WHERE id=%s", (request.form.get('nome'), local_id))
    conn.commit(); cursor.close(); conn.close()
    cache.delete('dados_dashboard')
    return redirect(url_for('index', tab='locais'))

@app.route('/locais/remover/<int:local_id>', methods=['POST'])
@role_required(['admin', 'gestor'])
def remover_local(local_id):
    conn = mysql.connection; cursor = conn.cursor(); cursor.execute("USE almoxarifado_db")
    try:
        cursor.execute("DELETE FROM locais WHERE id=%s", (local_id,))
        conn.commit()
        cache.delete('dados_dashboard')
    except: pass
    cursor.close(); conn.close()
    return redirect(url_for('index', tab='locais'))

# --- ROTAS DE PRODUTOS ---
@app.route('/adicionar', methods=['POST'])
@role_required(['admin', 'gestor'])
def adicionar_produto():
    nome = request.form.get('nome')
    quantidade = request.form['quantidade']
    local_id = request.form.get('local_id')
    if local_id == '0': local_id = None
    estoque_min = request.form['estoque_min']
    fornecedor_id = request.form.get('fornecedor_id')
    gestor_id = request.form.get('gestor_id')
    if fornecedor_id == '0': fornecedor_id = None
    if gestor_id == '0': gestor_id = None

    conn = mysql.connection
    cursor = conn.cursor(dictionary=True)
    cursor.execute("USE almoxarifado_db")
    
    cursor.execute("INSERT INTO produtos (nome, quantidade, local_id, estoque_min, fornecedor_id, gestor_id) VALUES (%s, %s, %s, %s, %s, %s)", 
                   (nome, quantidade, local_id, estoque_min, fornecedor_id, gestor_id))
    conn.commit()
    cache.delete('dados_dashboard')
    id_prod = cursor.lastrowid

    local_destino = None
    if local_id:
        cursor.execute("SELECT nome FROM locais WHERE id = %s", (local_id,))
        local_row = cursor.fetchone()
        local_destino = local_row['nome'] if local_row else None

    registrar_movimentacao(
        produto_id=id_prod,
        produto_nome=nome,
        tipo='cadastro',
        descricao='Item cadastrado no sistema',
        usuario_id=get_jwt_identity(),
        usuario_nome=get_jwt().get('nome') if get_jwt() else None,
        usuario_cargo=get_jwt().get('cargo') if get_jwt() else None,
        local_destino=local_destino,
        quantidade_anterior=0,
        quantidade_nova=int(quantidade)
    )
    
    if deve_alertar_reabastecimento(0, quantidade):
        registrar_movimentacao(
            produto_id=id_prod,
            produto_nome=nome,
            tipo='reabastecimento',
            descricao='Item reabastecido em estoque',
            usuario_id=get_jwt_identity(),
            usuario_nome=get_jwt().get('nome') if get_jwt() else None,
            usuario_cargo=get_jwt().get('cargo') if get_jwt() else None,
            quantidade_anterior=0,
            quantidade_nova=int(quantidade)
        )
        destinatarios = obter_destinatarios_alerta_reabastecimento(cursor)
        disparar_alerta_reabastecimento(id_prod, nome, 0, int(quantidade), destinatarios)

    if is_estoque_baixo(quantidade, estoque_min):
        destinatarios = obter_destinatarios_alerta(cursor)
        disparar_alerta_estoque_baixo(id_prod, nome, destinatarios)
    
    cursor.close(); conn.close()
    return redirect(url_for('index'))

@app.route('/editar/<int:produto_id>', methods=['POST'])
@jwt_required()
def editar_produto(produto_id):
    claims = get_jwt()
    role = claims.get('cargo')
    conn = mysql.connection
    cursor = conn.cursor(dictionary=True)
    cursor.execute("USE almoxarifado_db")
    
    cursor.execute("SELECT quantidade, nome, local_id, estoque_min, fornecedor_id, gestor_id FROM produtos WHERE id = %s", (produto_id,))
    prod_antigo = cursor.fetchone()
    qtd_antiga = prod_antigo['quantidade'] if prod_antigo else 0
    nome_prod = prod_antigo['nome'] if prod_antigo else "Produto"
    local_antigo = prod_antigo['local_id'] if prod_antigo else None
    estoque_min_antigo = prod_antigo['estoque_min'] if prod_antigo else 0

    nova_quantidade = 0
    novo_minimo = 0
    quantidade_reabastecida = request.form.get('quantidade_reabastecida', '0')
    quantidade_reabastecida = int(quantidade_reabastecida) if quantidade_reabastecida else 0
    
    if role == 'vendedor':
        nova_quantidade = int(request.form['quantidade'])
        cursor.execute("SELECT estoque_min FROM produtos WHERE id = %s", (produto_id,))
        res = cursor.fetchone()
        novo_minimo = res['estoque_min'] if res else 0
        cursor.execute("UPDATE produtos SET quantidade=%s WHERE id=%s", (nova_quantidade, produto_id))
    else:
        nome_prod = request.form.get('nome')
        nova_quantidade = calcular_quantidade_final(int(request.form['quantidade']), quantidade_reabastecida)
        local_id = request.form.get('local_id')
        if local_id == '0': local_id = None
        novo_minimo = int(request.form['estoque_min'])
        forn = request.form.get('fornecedor_id')
        gest = request.form.get('gestor_id')
        if forn == '0': forn = None
        if gest == '0': gest = None
        
        cursor.execute("UPDATE produtos SET nome=%s, quantidade=%s, local_id=%s, estoque_min=%s, fornecedor_id=%s, gestor_id=%s WHERE id=%s",
                       (nome_prod, nova_quantidade, local_id, novo_minimo, forn, gest, produto_id))
    
    conn.commit()
    cache.delete('dados_dashboard')

    if role != 'vendedor':
        registrar_movimentacao(
            produto_id=produto_id,
            produto_nome=nome_prod,
            tipo='alteracao',
            descricao='Dados do item alterados',
            usuario_id=get_jwt_identity(),
            usuario_nome=get_jwt().get('nome') if get_jwt() else None,
            usuario_cargo=get_jwt().get('cargo') if get_jwt() else None,
            quantidade_anterior=qtd_antiga,
            quantidade_nova=nova_quantidade
        )

        if local_antigo != (local_id if role != 'vendedor' else None):
            local_origem = None
            local_destino = None
            if local_antigo:
                cursor.execute("SELECT nome FROM locais WHERE id = %s", (local_antigo,))
                local_row = cursor.fetchone()
                local_origem = local_row['nome'] if local_row else None
            if local_id:
                cursor.execute("SELECT nome FROM locais WHERE id = %s", (local_id,))
                local_row = cursor.fetchone()
                local_destino = local_row['nome'] if local_row else None
            registrar_movimentacao(
                produto_id=produto_id,
                produto_nome=nome_prod,
                tipo='movimentacao',
                descricao='Item movimentado entre setores/galpões',
                usuario_id=get_jwt_identity(),
                usuario_nome=get_jwt().get('nome') if get_jwt() else None,
                usuario_cargo=get_jwt().get('cargo') if get_jwt() else None,
                local_origem=local_origem,
                local_destino=local_destino,
                quantidade_anterior=qtd_antiga,
                quantidade_nova=nova_quantidade
            )

    if deve_alertar_reabastecimento(qtd_antiga, nova_quantidade):
        registrar_movimentacao(
            produto_id=produto_id,
            produto_nome=nome_prod,
            tipo='reabastecimento',
            descricao='Item reabastecido em estoque',
            usuario_id=get_jwt_identity(),
            usuario_nome=get_jwt().get('nome') if get_jwt() else None,
            usuario_cargo=get_jwt().get('cargo') if get_jwt() else None,
            quantidade_anterior=qtd_antiga,
            quantidade_nova=nova_quantidade
        )
        destinatarios = obter_destinatarios_alerta_reabastecimento(cursor)
        disparar_alerta_reabastecimento(produto_id, nome_prod, qtd_antiga, nova_quantidade, destinatarios)

    if is_estoque_baixo(nova_quantidade, novo_minimo) and not is_estoque_baixo(qtd_antiga, novo_minimo):
        destinatarios = obter_destinatarios_alerta(cursor)
        disparar_alerta_estoque_baixo(produto_id, nome_prod, destinatarios)

    cursor.close(); conn.close()
    return redirect(url_for('index'))

@app.route('/remover/<int:produto_id>', methods=['POST'])
@role_required(['admin', 'gestor'])
def remover_produto(produto_id):
    conn = mysql.connection; cursor = conn.cursor(dictionary=True); cursor.execute("USE almoxarifado_db")
    cursor.execute("SELECT nome, quantidade FROM produtos WHERE id = %s", (produto_id,))
    produto_removido = cursor.fetchone()
    cursor.execute("DELETE FROM produtos WHERE id = %s", (produto_id,))
    conn.commit()
    registrar_movimentacao(
        produto_id=produto_id,
        produto_nome=produto_removido['nome'] if produto_removido else None,
        tipo='remocao',
        descricao='Item removido do sistema',
        usuario_id=get_jwt_identity(),
        usuario_nome=get_jwt().get('nome') if get_jwt() else None,
        usuario_cargo=get_jwt().get('cargo') if get_jwt() else None,
        quantidade_anterior=produto_removido['quantidade'] if produto_removido else None,
        quantidade_nova=0
    )
    cursor.close(); conn.close()
    cache.delete('dados_dashboard')
    return redirect(url_for('index'))

@app.route('/realizar_saida/<int:produto_id>', methods=['POST'])
@jwt_required()
def realizar_saida(produto_id):
    try: qtd_saida = int(request.form.get('quantidade_saida'))
    except: return "Quantidade inválida", 400

    conn = mysql.connection
    cursor = conn.cursor(dictionary=True)
    cursor.execute("USE almoxarifado_db")
    cursor.execute("SELECT quantidade, estoque_min, nome FROM produtos WHERE id = %s", (produto_id,))
    produto = cursor.fetchone()
    
    if produto:
        if qtd_saida > produto['quantidade']: 
            cursor.close(); conn.close()
            return "Erro: Estoque insuficiente", 400
        novo_estoque = produto['quantidade'] - qtd_saida
        em_falta = request.form.get('em_falta') == '1' or novo_estoque <= 0
        cursor.execute("UPDATE produtos SET quantidade = %s, em_falta = %s WHERE id = %s", (novo_estoque, int(em_falta), produto_id))
        conn.commit()
        cache.delete('dados_dashboard')

        registrar_movimentacao(
            produto_id=produto_id,
            produto_nome=produto['nome'],
            tipo='saida',
            descricao='Solicitação/baixa de item registrada',
            usuario_id=get_jwt_identity(),
            usuario_nome=get_jwt().get('nome') if get_jwt() else None,
            usuario_cargo=get_jwt().get('cargo') if get_jwt() else None,
            quantidade_anterior=produto['quantidade'],
            quantidade_nova=novo_estoque
        )
        
        if is_estoque_baixo(novo_estoque, produto['estoque_min']) and not is_estoque_baixo(produto['quantidade'], produto['estoque_min']):
            destinatarios = obter_destinatarios_alerta(cursor)
            disparar_alerta_estoque_baixo(produto_id, produto['nome'], destinatarios)
            
    cursor.close(); conn.close()
    return redirect(url_for('index'))

# --- ROTAS DE FORNECEDORES ---
@app.route('/fornecedores/adicionar', methods=['POST'])
@role_required(['admin', 'gestor'])
def adicionar_fornecedor():
    conn = mysql.connection; cursor = conn.cursor(); cursor.execute("USE almoxarifado_db")
    cursor.execute("INSERT INTO fornecedores (nome, contato_nome, telefone, email) VALUES (%s, %s, %s, %s)", 
                   (request.form.get('nome'), request.form.get('contato_nome'), request.form.get('telefone'), request.form.get('email')))
    conn.commit(); cursor.close(); conn.close()
    cache.delete('dados_dashboard')
    return redirect(url_for('index', tab='fornecedores'))

@app.route('/fornecedores/editar/<int:fornecedor_id>', methods=['POST'])
@role_required(['admin', 'gestor'])
def editar_fornecedor(fornecedor_id):
    conn = mysql.connection; cursor = conn.cursor(); cursor.execute("USE almoxarifado_db")
    cursor.execute("UPDATE fornecedores SET nome=%s, contato_nome=%s, telefone=%s, email=%s WHERE id=%s", 
                   (request.form.get('nome'), request.form.get('contato_nome'), request.form.get('telefone'), request.form.get('email'), fornecedor_id))
    conn.commit(); cursor.close(); conn.close()
    cache.delete('dados_dashboard')
    return redirect(url_for('index', tab='fornecedores'))

@app.route('/fornecedores/remover/<int:fornecedor_id>', methods=['POST'])
@role_required(['admin', 'gestor'])
def remover_fornecedor(fornecedor_id):
    conn = mysql.connection; cursor = conn.cursor(); cursor.execute("USE almoxarifado_db")
    try: cursor.execute("DELETE FROM fornecedores WHERE id=%s", (fornecedor_id,)); conn.commit()
    except: pass
    cursor.close(); conn.close()
    return redirect(url_for('index', tab='fornecedores'))

# --- ROTAS DE USUÁRIOS ---
@app.route('/usuarios/adicionar', methods=['POST'])
@role_required(['admin', 'gestor'])
def adicionar_usuario():
    cargo_logado = get_jwt().get('cargo')
    cargo_alvo = request.form.get('cargo')
    if not pode_editar_usuario(cargo_logado, cargo_alvo):
        return redirect(url_for('index', tab='usuarios', erro_msg='Você não tem permissão para criar usuários administradores.'))

    conn = mysql.connection; cursor = conn.cursor(); cursor.execute("USE almoxarifado_db")
    try:
        sh = generate_password_hash(request.form.get('senha'))
        cursor.execute("INSERT INTO usuarios (nome, email, telefone, senha, cargo) VALUES (%s, %s, %s, %s, %s)",
                       (request.form.get('nome'), request.form.get('email'), request.form.get('telefone') or None, sh, cargo_alvo))
        conn.commit()
        cache.delete('dados_dashboard')
        threading.Thread(target=enviar_boas_vindas_thread, args=[request.form.get('nome'), request.form.get('email'), request.form.get('senha')]).start()
    except Exception as e: print(f"Erro: {e}")
    finally: cursor.close(); conn.close()
    return redirect(url_for('index', tab='usuarios'))

@app.route('/usuarios/editar/<int:usuario_id>', methods=['POST'])
@role_required(['admin', 'gestor'])
def editar_usuario(usuario_id):
    cargo_logado = get_jwt().get('cargo')
    cargo_alvo = request.form.get('cargo')
    if not pode_editar_usuario(cargo_logado, cargo_alvo):
        return redirect(url_for('index', tab='usuarios', erro_msg='Você não tem permissão para editar usuários administradores.'))

    conn = mysql.connection; cursor = conn.cursor(); cursor.execute("USE almoxarifado_db")
    try:
        if request.form.get('senha'):
            sh = generate_password_hash(request.form.get('senha'))
            cursor.execute("UPDATE usuarios SET nome=%s, email=%s, telefone=%s, cargo=%s, senha=%s WHERE id=%s",
                           (request.form.get('nome'), request.form.get('email'), request.form.get('telefone') or None, cargo_alvo, sh, usuario_id))
        else:
            cursor.execute("UPDATE usuarios SET nome=%s, email=%s, telefone=%s, cargo=%s WHERE id=%s",
                           (request.form.get('nome'), request.form.get('email'), request.form.get('telefone') or None, cargo_alvo, usuario_id))
        conn.commit()
        cache.delete('dados_dashboard')
    except: pass
    cursor.close(); conn.close()
    return redirect(url_for('index', tab='usuarios'))

@app.route('/usuarios/remover/<int:usuario_id>', methods=['POST'])
@jwt_required()
def remover_usuario(usuario_id):
    claims = get_jwt()
    cargo_usuario_logado = claims.get('cargo')

    conn = mysql.connection
    cursor = conn.cursor(dictionary=True)
    cursor.execute("USE almoxarifado_db")
    try:
        cursor.execute("SELECT cargo FROM usuarios WHERE id = %s", (usuario_id,))
        usuario_alvo = cursor.fetchone()
        mensagem = mensagem_permissao_remocao_usuario(cargo_usuario_logado, usuario_alvo['cargo'] if usuario_alvo else None)
        if mensagem:
            return redirect(url_for('index', tab='usuarios', erro_msg=mensagem))

        if usuario_alvo and usuario_alvo['cargo'] == 'admin':
            cursor.execute("SELECT COUNT(*) as qtd FROM usuarios WHERE cargo = 'admin'")
            if cursor.fetchone()['qtd'] <= 1:
                return redirect(url_for('index', tab='usuarios', erro_msg="ERRO: Impossível excluir o único Admin."))

        cursor.execute("DELETE FROM usuarios WHERE id = %s", (usuario_id,))
        conn.commit()
        cache.delete('dados_dashboard')
    except Exception as e:
        print(e)
    finally:
        cursor.close(); conn.close()
    return redirect(url_for('index', tab='usuarios'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=True)