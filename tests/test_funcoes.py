"""
Testes das funções do AdLibHarvest que não dependem do navegador.

Uso (na pasta do repositório):
    python tests/test_funcoes.py
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import script as sc


def test_clean_caption_remove_interface():
    bruto = "Patrocinado\nPeça já o seu!\n0:05 / 0:15\nwww.exemplo.com.br\nSaiba mais\nMenos de 100 impressões"
    assert sc.clean_caption(bruto) == "Peça já o seu!"


def test_clean_caption_preserva_texto_parecido_com_interface():
    # a filtragem é por linha inteira: frases com '.com' ou 'saiba mais' no meio ficam
    texto = "Acesse exemplo.com e saiba mais sobre a promoção."
    assert sc.clean_caption(texto) == texto


def test_media_key_ignora_parametros():
    a = "https://video.fbcdn.net/v/t42/arquivo_n.mp4?_nc_cat=1&oh=abc"
    b = "https://scontent.fbcdn.net/v/t42/arquivo_n.mp4?oh=xyz"
    assert sc.media_key(a) == sc.media_key(b) == "arquivo_n.mp4"


def test_strip_byte_range():
    url = "https://video.fbcdn.net/v/a.mp4?bytestart=0&byteend=999&oh=abc"
    assert sc.strip_byte_range(url) == "https://video.fbcdn.net/v/a.mp4?oh=abc"


def test_ext_from_content_type():
    assert sc.ext_from_content_type("video/mp4", ".bin") == ".mp4"
    assert sc.ext_from_content_type("image/jpeg", ".bin") == ".jpg"
    assert sc.ext_from_content_type(None, ".jpg") == ".jpg"


def _anuncio(cards, body="Texto do anúncio"):
    return {"ad_archive_id": "111", "page_id": "999", "page_name": "Marca Teste",
            "publisher_platform": ["facebook", "instagram"],
            "snapshot": {"body": {"text": body}, "cards": cards, "display_format": "DCO"}}


def test_adindex_carrossel_misto_sem_capas_e_sem_duplicatas():
    cards = [
        {"video_hd_url": "https://x.fbcdn.net/v1.mp4", "video_sd_url": "https://x.fbcdn.net/v1_sd.mp4",
         "video_preview_image_url": "https://x.fbcdn.net/capa1.jpg", "original_image_url": "https://x.fbcdn.net/capa1.jpg"},
        {"original_image_url": "https://x.fbcdn.net/img1.jpg", "resized_image_url": "https://x.fbcdn.net/img1_p.jpg"},
        {"original_image_url": "https://x.fbcdn.net/img1.jpg"},  # versão repetida
    ]
    idx = sc.AdIndex()
    idx.feed_text(json.dumps({"data": {"resultados": [_anuncio(cards)]}}))
    e = idx.get("111")
    assert e["videos"] == ["https://x.fbcdn.net/v1.mp4"]       # HD, sem a versão SD
    assert e["images"] == ["https://x.fbcdn.net/img1.jpg"]     # original, sem capa e sem duplicata
    assert e["platforms"] == ["FACEBOOK", "INSTAGRAM"]
    assert e["body"] == "Texto do anúncio"


def test_adindex_legenda_dinamica_usa_primeira_versao():
    cards = [{"original_image_url": "https://x.fbcdn.net/a.jpg", "body": "Texto da versão 1"}]
    idx = sc.AdIndex()
    idx.feed_text(json.dumps(_anuncio(cards, body="{{product.brand}}")))
    assert idx.get("111")["body"] == "Texto da versão 1"


def test_adindex_prefixo_e_html():
    idx = sc.AdIndex()
    idx.feed_text("for (;;);" + json.dumps(_anuncio([{"original_image_url": "https://x.fbcdn.net/a.jpg"}])))
    assert idx.get("111") is not None
    idx2 = sc.AdIndex()
    idx2.feed_text('<html><script type="application/json">%s</script></html>'
                   % json.dumps(_anuncio([{"original_image_url": "https://x.fbcdn.net/b.jpg"}])))
    assert idx2.get("111")["images"] == ["https://x.fbcdn.net/b.jpg"]


def test_nome_da_marca():
    idx = sc.AdIndex()
    idx.feed_text(json.dumps(_anuncio([{"original_image_url": "https://x.fbcdn.net/a.jpg"}])))
    base = "https://www.facebook.com/ads/library/?country=BR&"
    assert sc.nome_da_marca(base + "view_all_page_id=999", idx, "Biblioteca de Anúncios") == "Marca Teste"
    assert sc.nome_da_marca(base + "view_all_page_id=123", idx, "Biblioteca de Anúncios") == "Pagina_123"
    assert sc.nome_da_marca(base + "q=sorvete", idx, "Biblioteca de Anúncios") == "sorvete"
    assert sc.clean_filename('Marca: "Teste"?') == "Marca Teste"


if __name__ == "__main__":
    testes = [f for nome, f in sorted(globals().items()) if nome.startswith("test_")]
    falhas = 0
    for t in testes:
        try:
            t()
            print("ok   ", t.__name__)
        except AssertionError as e:
            falhas += 1
            print("FALHA", t.__name__, e)
    print(f"{len(testes) - falhas} de {len(testes)} testes passaram")
    sys.exit(1 if falhas else 0)
