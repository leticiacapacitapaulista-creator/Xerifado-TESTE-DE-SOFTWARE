from app import mensagem_permissao_remocao_usuario, pode_editar_usuario


def test_mensagem_permissao_remocao_usuario_bloqueia_gestor_para_admin():
    assert mensagem_permissao_remocao_usuario('gestor', 'admin') == 'Você não tem permissão para remover usuários administradores.'


def test_pode_editar_usuario_restringe_gestor_para_admin():
    assert pode_editar_usuario('gestor', 'admin') is False
    assert pode_editar_usuario('gestor', 'vendedor') is True
    assert pode_editar_usuario('admin', 'admin') is True
