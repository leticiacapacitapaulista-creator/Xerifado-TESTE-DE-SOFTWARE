def test_login_contem_html(client):

    response = client.get("/login")

    print("\n===== TESTE CT02 =====")
    print("Objetivo: Verificar se a página de login retorna HTML")
    print("Status Code:", response.status_code)
    print("Contém HTML:", b"<html" in response.data.lower())
    print("======================\n")

    assert response.status_code == 200
    assert b"<html" in response.data.lower()


def test_esqueci_senha_exibe_formulario(client):
    response = client.get("/esqueci_senha")

    assert response.status_code == 200
    assert b"esqueci a senha" in response.data.lower()
    assert b"email" in response.data.lower()


def test_solicitar_reset_senha_retorna_mensagem(client):
    response = client.post(
        "/esqueci_senha",
        data={"email": "admin@admin.com"},
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"codigo" in response.data.lower() or b"telefone" in response.data.lower()


def test_login_credenciais_invalidas(client, monkeypatch):
    class FakeCursor:
        def execute(self, *args, **kwargs):
            return None

        def fetchone(self):
            return None

        def close(self):
            return None

    class FakeConnection:
        def cursor(self, dictionary=True):
            return FakeCursor()

        def close(self):
            return None

    monkeypatch.setattr("app.driver.connect", lambda **kwargs: FakeConnection())

    response = client.post(
        "/login",
        data={"email": "usuario_invalido@teste.com", "password": "senha_errada"},
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert "credenciais inválidas".encode("utf-8") in response.data.lower()

    