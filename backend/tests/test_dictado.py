from app.modules.odontogram.dictado import interpretar


def _h(texto):
    return [(h.fdi_number, h.surface, h.condition) for h in interpretar(texto).hallazgos]


def test_frase_completa():
    assert _h("pieza 36 caries oclusal, 11 corona, 46 mesial y distal restauración, falta el 18") == [
        ("36", "oclusal", "caries"),
        ("11", "whole", "corona"),
        ("46", "mesial", "restauracion"),
        ("46", "distal", "restauracion"),
        ("18", "whole", "ausente"),
    ]


def test_numeros_en_palabras_y_sinonimos():
    assert _h("treinta y seis tratamiento de conducto") == [("36", "whole", "endodoncia")]
    assert _h("once fractura incisal") == [("11", "oclusal", "fractura")]
    assert _h("tres seis resina vestibular") == [("36", "vestibular", "restauracion")]
    assert _h("el 48 para extraer") == [("48", "whole", "extraccion_indicada")]
    assert _h("veintiséis sellante") == [("26", "whole", "sellante")]


def test_varias_piezas_y_siglas():
    assert _h("16 y 26 caries oclusal") == [("16", "oclusal", "caries"), ("26", "oclusal", "caries")]
    assert _h("37 MOD amalgama") == [("37", "mesial", "restauracion"), ("37", "oclusal", "restauracion"), ("37", "distal", "restauracion")]
    assert _h("14 mesio oclusal caries") == [("14", "oclusal", "caries"), ("14", "mesial", "caries")]


def test_lo_que_no_entiende_se_devuelve():
    r = interpretar("paciente refiere dolor. 21 corona. pieza 99 caries")
    assert [(h.fdi_number, h.condition) for h in r.hallazgos] == [("21", "corona")]
    assert "paciente refiere dolor" in r.sin_entender
    assert any("99" in x for x in r.sin_entender)


async def test_ruta(client):
    r = await client.post("/api/v1/auth/login", json={"email": "admin@clinicatest.io", "password": "Admin123!"})
    h = {"Authorization": f"Bearer {r.json()['access_token']}"}
    r = await client.post("/api/v1/odontogram/dictation", json={"texto": "36 caries oclusal"}, headers=h)
    assert r.status_code == 200
    assert r.json()["hallazgos"] == [{"fdi_number": "36", "surface": "oclusal", "condition": "caries"}]
