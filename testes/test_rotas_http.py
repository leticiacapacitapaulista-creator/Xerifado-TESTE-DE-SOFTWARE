def test_rota_inexistente(client):
    response = client.get("/rota_inexistente")

    print("\n===== TESTE CT03 =====")
    print("Status Code:", response.status_code)
    print("======================\n")

    assert response.status_code == 404
