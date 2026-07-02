from app import obter_destinatarios_alerta, obter_destinatarios_alerta_reabastecimento, get_alertas_reabastecimento, registrar_movimentacao


class CursorSimulado:
    def __init__(self, rows):
        self._rows = rows

    def execute(self, query, params=None):
        return None

    def fetchone(self):
        return self._rows.pop(0) if self._rows else None

    def fetchall(self):
        rows = list(self._rows)
        self._rows = []
        return rows


def test_obter_destinatarios_alerta_aceita_cursor_com_dicionarios():
    cursor = CursorSimulado([
        {"valor": "alerta@teste.com"},
        [{"email": "gestor@teste.com"}, {"email": "admin@teste.com"}],
    ])

    destinatarios = obter_destinatarios_alerta(cursor)

    assert destinatarios == ["alerta@teste.com", "gestor@teste.com", "admin@teste.com"]


def test_obter_destinatarios_alerta_reabastecimento_inclui_gestor_e_vendedor():
    cursor = CursorSimulado([
        {"valor": "alerta@teste.com"},
        [{"email": "gestor@teste.com"}, {"email": "vendedor@teste.com"}],
    ])

    destinatarios = obter_destinatarios_alerta_reabastecimento(cursor)

    assert destinatarios == ["alerta@teste.com", "gestor@teste.com", "vendedor@teste.com"]


def test_registrar_movimentacao_cria_registro_com_tipo_e_usuario():
    registro_id = registrar_movimentacao(
        produto_id=1,
        produto_nome='Caneta',
        tipo='cadastro',
        descricao='Item cadastrado',
        usuario_id=1,
        usuario_nome='Admin',
        usuario_cargo='admin',
        local_destino='Setor A'
    )

    assert isinstance(registro_id, int)
    assert registro_id > 0


def test_get_alertas_reabastecimento_filtra_registros_reabastecimento():
    class CursorSimuladoBanco:
        def __init__(self, rows):
            self._rows = rows

        def execute(self, query, params=None):
            return None

        def fetchall(self):
            return list(self._rows)

    cursor = CursorSimuladoBanco([
        {'tipo': 'saida', 'produto_nome': 'Caneta'},
        {'tipo': 'reabastecimento', 'produto_nome': 'Caderno'}
    ])

    alertas = get_alertas_reabastecimento(cursor)

    assert len(alertas) == 1
    assert alertas[0]['produto_nome'] == 'Caderno'
