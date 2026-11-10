"""
AdLibHarvest - coletor da Meta Ad Library para fins acadêmicos.

Uso:
    python script.py                       # pede a URL no terminal
    python script.py --url "<URL>"         # URL direto na linha de comando
    python script.py --url "<URL>" --debug # salva as respostas brutas da Meta em <marca>/_debug

Estratégia de coleta de mídia (em camadas, da mais para a menos confiável):
  1. JSON da própria Meta: a página e as requisições GraphQL trazem, para cada
     Library ID, o "snapshot" do anúncio com TODAS as variações (cards/vídeos/imagens),
     inclusive as que ainda não foram renderizadas na tela (lazy loading).
  2. Rede: arquivos de vídeo servidos pela CDN (fbcdn.net) enquanto o modal do anúncio
     está aberto são atribuídos ao Library ID em processamento.
  3. DOM: <video>/<img> visíveis no modal (ou no card), coletados a cada passo da rolagem.
"""

import argparse
import asyncio
import json
import os
import re
import urllib.request
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

import pandas as pd
from playwright.async_api import async_playwright

COLUNAS = [
    'Marca', 'Library ID', 'Link Permanente', 'Status', 'Data de Lançamento', 'Tipo de Mídia',
    'Veiculação Facebook', 'Veiculação Instagram', 'Veiculação Messenger', 'Veiculação Audience Network',
    'Veiculação Threads', 'Veiculação WhatsApp', 'Uso por Múltiplos', 'Qtd Criativos (A/B)', 'É Dinâmico',
    'Texto da Legenda',
]

# ---------------------------------------------------------------------------
# Utilidades gerais
# ---------------------------------------------------------------------------

def clean_filename(name):
    return re.sub(r'[\\/*?:"<>|]', "", name).strip() or "Marca_Extraida"


def media_key(url):
    """Chave de deduplicação: o mesmo arquivo da CDN aparece com parâmetros de
    tamanho/assinatura diferentes, mas o nome do arquivo no caminho é o mesmo."""
    try:
        return os.path.basename(urlparse(url).path) or url
    except Exception:
        return url


def strip_byte_range(url):
    """Remove bytestart/byteend que o player acrescenta às URLs de vídeo, para
    baixar o arquivo inteiro e não apenas um pedaço."""
    try:
        u = urlparse(url)
        q = [(k, v) for k, v in parse_qsl(u.query, keep_blank_values=True)
             if k not in ('bytestart', 'byteend')]
        return urlunparse(u._replace(query=urlencode(q)))
    except Exception:
        return url


def ext_from_content_type(ctype, default):
    ctype = (ctype or '').lower()
    if 'mp4' in ctype:
        return '.mp4'
    if 'webm' in ctype:
        return '.webm'
    if 'png' in ctype:
        return '.png'
    if 'webp' in ctype:
        return '.webp'
    if 'jpeg' in ctype or 'jpg' in ctype:
        return '.jpg'
    return default


async def download_media(context, url, path_sem_ext, default_ext):
    """Baixa usando a sessão do próprio navegador (mesmos cookies/UA); se falhar,
    tenta urllib. Retorna o caminho salvo ou None."""
    try:
        resp = await context.request.get(url, timeout=90000)
        if resp.ok:
            body = await resp.body()
            if body:
                path = path_sem_ext + ext_from_content_type(resp.headers.get('content-type'), default_ext)
                with open(path, 'wb') as f:
                    f.write(body)
                return path
    except Exception:
        pass
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=60) as response:
            body = response.read()
            path = path_sem_ext + ext_from_content_type(response.headers.get('Content-Type'), default_ext)
            with open(path, 'wb') as f:
                f.write(body)
            return path
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Higienização da legenda
# ---------------------------------------------------------------------------

CTA_TEXTOS = {
    'saiba mais', 'learn more', 'fale conosco', 'contact us', 'entre em contato', 'entrar em contato',
    'see menu', 'ver menu', 'ver cardápio', 'comprar agora', 'shop now', 'compre agora', 'peça agora',
    'pedir agora', 'order now', 'enviar mensagem', 'send message', 'send whatsapp message',
    'enviar mensagem pelo whatsapp', 'cadastre-se', 'sign up', 'inscreva-se', 'subscribe', 'baixar',
    'download', 'instalar agora', 'install now', 'usar app', 'use app', 'abrir link', 'open link',
    'ver mais', 'see more', 'assistir mais', 'watch more', 'reservar', 'reservar agora', 'book now',
    'obter oferta', 'get offer', 'ver oferta', 'ligar agora', 'call now', 'candidate-se', 'apply now',
    'obter rota', 'get directions', 'como chegar', 'jogar', 'play game', 'doar agora', 'donate now',
    'ouvir agora', 'listen now', 'solicitar horário', 'request time', 'obter cotação', 'get quote',
    'aproveite', 'aproveitar', 'ver detalhes do anúncio', 'ver resumo',
}

RE_IMPRESSOES = re.compile(
    r'(baixo n[úu]mero de impress|menos de\s+[\d\.,]+\s*(mil\s+)?impress|low impression|'
    r'fewer than\s+[\d,\.]+\s*impressions)', re.IGNORECASE)
RE_TEMPO_VIDEO = re.compile(r'^\d+:\d+\s*/\s*\d+:\d+$')
RE_URL_SOLTA = re.compile(r'^(https?://)?(www\.)?[\w\-]+(\.[\w\-]+)+(/\S*)?$', re.IGNORECASE)
RE_CABECALHO = re.compile(
    r'^(ativo|inativo|patrocinado|sponsored|plataformas|identifica[çc][ãa]o da biblioteca.*|'
    r'veicula[çc][ãa]o iniciada.*|esse an[úu]ncio tem v[áa]rias vers[õo]es|'
    r'\d+\s+an[úu]ncios? usa(m)? esse criativo.*|curtidas e coment[áa]rios.*|compartilhar)$',
    re.IGNORECASE)


def clean_caption(text):
    """Remove linhas de interface da Meta. A filtragem é por LINHA INTEIRA (não por
    substring), para não cortar legendas que contenham, p.ex., 'menos de' ou '.com'."""
    if not text:
        return ""
    out = []
    for raw in text.replace('\r', '').split('\n'):
        line = raw.replace('​', '').strip()
        if not line:
            if out and out[-1] != '':
                out.append('')
            continue
        low = line.casefold()
        if RE_IMPRESSOES.search(line):
            continue
        if RE_TEMPO_VIDEO.match(line) or RE_URL_SOLTA.match(line) or RE_CABECALHO.match(line):
            continue
        if low in CTA_TEXTOS:
            continue
        out.append(line)
    return "\n".join(out).strip()[:3000]


# ---------------------------------------------------------------------------
# Índice de anúncios a partir do JSON da Meta
# ---------------------------------------------------------------------------

class AdIndex:
    """Guarda, por Library ID, o snapshot do anúncio extraído do JSON que a Meta envia
    ao navegador (HTML inicial + respostas GraphQL/async)."""

    def __init__(self):
        self.ads = {}

    # --- extração -------------------------------------------------------
    def feed_text(self, text):
        if not text or 'ad_archive_id' not in text:
            return
        if text.startswith('for (;;);'):
            text = text[len('for (;;);'):]
        found = False
        for chunk in self._json_chunks(text):
            try:
                obj = json.loads(chunk)
            except Exception:
                continue
            self._walk(obj)
            found = True
        if not found:
            self._regex_fallback(text)

    @staticmethod
    def _json_chunks(text):
        stripped = text.lstrip()
        if stripped.startswith('<'):
            # HTML: blocos <script type="application/json">
            for m in re.finditer(r'<script[^>]*type="application/json"[^>]*>(.*?)</script>', text, re.S):
                if 'ad_archive_id' in m.group(1):
                    yield m.group(1)
        else:
            yield text
            # GraphQL às vezes devolve vários JSON separados por quebra de linha
            if '\n' in text:
                for line in text.split('\n'):
                    if 'ad_archive_id' in line:
                        yield line

    def _walk(self, obj):
        stack = [obj]
        while stack:
            cur = stack.pop()
            if isinstance(cur, dict):
                ad_id = cur.get('ad_archive_id') or cur.get('adArchiveID')
                snap = cur.get('snapshot')
                if ad_id and isinstance(snap, dict):
                    self._register(str(ad_id), cur, snap)
                stack.extend(cur.values())
            elif isinstance(cur, list):
                stack.extend(cur)

    def _register(self, ad_id, ad, snap):
        videos, images, thumbs, bodies = [], [], [], []

        def add_video(d):
            url = d.get('video_hd_url') or d.get('video_sd_url')
            if url:
                videos.append(url)
            th = d.get('video_preview_image_url')
            if th:
                thumbs.append(th)

        def add_image(d):
            url = d.get('original_image_url') or d.get('resized_image_url')
            if url:
                images.append(url)

        for v in snap.get('videos') or []:
            if isinstance(v, dict):
                add_video(v)
        for im in snap.get('images') or []:
            if isinstance(im, dict):
                add_image(im)
        for c in snap.get('cards') or []:
            if not isinstance(c, dict):
                continue
            # card de vídeo: só o vídeo; card sem vídeo: a imagem
            if c.get('video_hd_url') or c.get('video_sd_url'):
                add_video(c)
            else:
                add_image(c)
            b = c.get('body')
            if isinstance(b, dict):
                b = b.get('text')
            if isinstance(b, str) and b.strip():
                bodies.append(b)

        body = snap.get('body')
        if isinstance(body, dict):
            body = body.get('text') or (body.get('markup') or {}).get('__html')
        if isinstance(body, str):
            body = re.sub(r'<br\s*/?>', '\n', body)
            body = re.sub(r'<[^>]+>', '', body)
        # Em anúncios dinâmicos (DCO), o corpo principal pode vir como template {{...}};
        # nesse caso usamos o texto da primeira versão, que é a exibida no card.
        if not isinstance(body, str) or not body.strip() or '{{' in body:
            body = bodies[0] if bodies else ''

        entry = {
            'videos': list(dict.fromkeys(videos)),
            'images': list(dict.fromkeys(images)),
            'thumbs': list(dict.fromkeys(thumbs)),
            'body': body or '',
            'platforms': [str(p).upper() for p in (ad.get('publisher_platform') or ad.get('publisherPlatform') or [])],
            'display_format': snap.get('display_format') or '',
            'page_id': str(ad.get('page_id') or snap.get('page_id') or ''),
            'page_name': ad.get('page_name') or snap.get('page_name') or '',
        }
        old = self.ads.get(ad_id)
        if old is None or (len(entry['videos']) + len(entry['images'])) >= (len(old['videos']) + len(old['images'])):
            # mantém a versão mais completa, preservando o que só existia na antiga
            if old:
                for k in ('videos', 'images', 'thumbs'):
                    entry[k] = list(dict.fromkeys(entry[k] + old[k]))
                entry['body'] = entry['body'] or old['body']
                entry['platforms'] = entry['platforms'] or old['platforms']
            self.ads[ad_id] = entry
        else:
            for k in ('videos', 'images', 'thumbs'):
                old[k] = list(dict.fromkeys(old[k] + entry[k]))

    def _regex_fallback(self, text):
        """Se o texto não for JSON válido, associa URLs ao ad_archive_id mais próximo
        que as precede no texto."""
        marks = [(m.start(), m.group(1)) for m in re.finditer(r'"ad_archive_id"\s*:\s*"(\d+)"', text)]
        if not marks:
            return
        for i, (pos, ad_id) in enumerate(marks):
            end = marks[i + 1][0] if i + 1 < len(marks) else len(text)
            seg = text[pos:end]
            un = lambda s: json.loads('"' + s + '"')
            vids, imgs, ths = [], [], []
            for m in re.finditer(r'"video_(?:hd|sd)_url"\s*:\s*"((?:[^"\\]|\\.)+)"', seg):
                vids.append(un(m.group(1)))
            for m in re.finditer(r'"original_image_url"\s*:\s*"((?:[^"\\]|\\.)+)"', seg):
                imgs.append(un(m.group(1)))
            for m in re.finditer(r'"video_preview_image_url"\s*:\s*"((?:[^"\\]|\\.)+)"', seg):
                ths.append(un(m.group(1)))
            # hd e sd do mesmo vídeo têm nomes diferentes; mantemos 1 por par (o primeiro = hd)
            vids_unicos = []
            for m in re.finditer(r'"video_hd_url"\s*:\s*"((?:[^"\\]|\\.)+)"', seg):
                vids_unicos.append(un(m.group(1)))
            if not vids_unicos:
                vids_unicos = vids
            entry = self.ads.setdefault(ad_id, {'videos': [], 'images': [], 'thumbs': [], 'body': '',
                                                'platforms': [], 'display_format': '',
                                                'page_id': '', 'page_name': ''})
            entry['videos'] = list(dict.fromkeys(entry['videos'] + vids_unicos))
            entry['images'] = list(dict.fromkeys(entry['images'] + imgs))
            entry['thumbs'] = list(dict.fromkeys(entry['thumbs'] + ths))

    def get(self, ad_id):
        return self.ads.get(str(ad_id))

    def page_name(self, page_id):
        """Nome da página anunciante (ignora nomes de criadores em parcerias)."""
        for e in self.ads.values():
            if e.get('page_id') == str(page_id) and e.get('page_name'):
                return e['page_name']
        return ''


def nome_da_marca(url, index, title):
    """Nome da pasta/relatório. Prioridade: nome da página no JSON da Meta >
    termo pesquisado > ID da página. Sempre diferente entre marcas distintas."""
    q = dict(parse_qsl(urlparse(url).query))
    page_id = q.get('view_all_page_id', '')
    if page_id:
        nome = index.page_name(page_id)
        return nome if nome else f"Pagina_{page_id}"
    if q.get('q'):
        return q['q']
    if '|' in title:
        return title.split('|')[-1].strip()
    return "Marca_Extraida"


# ---------------------------------------------------------------------------
# Trechos JavaScript executados na página
# ---------------------------------------------------------------------------

JS_MARCAR_CARDS = r'''() => {
    let res = [];
    for (let span of document.querySelectorAll('span')) {
        const t = span.innerText || '';
        if (!t.includes('Identificação da biblioteca:')) continue;
        if (span.closest('div[role="dialog"]')) continue;
        let c = span;
        for (let i = 0; i < 8; i++) { if (c.parentElement) c = c.parentElement; }
        if (c.hasAttribute('data-adlib-id')) continue;
        const m = (c.innerText || '').match(/Identificação da biblioteca:\s*(\d+)/);
        if (!m) continue;
        if (res.includes(m[1])) continue;
        c.setAttribute('data-adlib-id', m[1]);
        res.push(m[1]);
    }
    return res;
}'''

# Corpo do anúncio = texto entre "Patrocinado" e a primeira mídia do card.
# Tudo que fica abaixo da mídia (URL de destino, título, CTA) é ignorado.
JS_LEGENDA_DOM = r'''(card) => {
    const all = Array.from(card.querySelectorAll('*'));
    const isMedia = el => el.tagName === 'VIDEO' ||
        (el.tagName === 'IMG' && Math.max(el.naturalWidth || 0, el.getBoundingClientRect().width) >= 150);
    const after = (a, b) => !!(a.compareDocumentPosition(b) & Node.DOCUMENT_POSITION_FOLLOWING);
    const sponsor = all.find(e => e.childElementCount === 0 &&
        /^(Patrocinado|Sponsored)$/.test((e.textContent || '').trim()));
    let stop = all.find(e => isMedia(e) && (!sponsor || after(sponsor, e)));
    if (!stop) {
        stop = all.find(e => (!sponsor || after(sponsor, e)) &&
            (e.matches('a[href*="l.facebook.com"]') || e.matches('div[role="button"]') || e.tagName === 'BUTTON'));
    }
    const inRange = el => (!sponsor || after(sponsor, el)) && (!stop || after(el, stop));

    const pre = Array.from(card.querySelectorAll('div[style*="white-space: pre-wrap"], div[style*="white-space:pre-wrap"]'))
        .filter(inRange);
    if (pre.length) {
        // descarta divs aninhadas (pega só as mais externas)
        const top = pre.filter(d => !pre.some(o => o !== d && o.contains(d)));
        return top.map(d => d.innerText).join('\n');
    }
    const walker = document.createTreeWalker(card, NodeFilter.SHOW_TEXT);
    const parts = [];
    let n;
    while ((n = walker.nextNode())) {
        const txt = (n.textContent || '').trim();
        if (!txt) continue;
        const p = n.parentElement;
        if (!p || !inRange(p)) continue;
        if (p.closest('a[href*="l.facebook.com"], div[role="button"], button')) continue;
        if (sponsor && (p === sponsor || p.contains(sponsor))) continue;
        if (parts[parts.length - 1] !== txt) parts.push(txt);
    }
    return parts.join('\n');
}'''

# Coleta mídias do DOM (ignora ícones/avatares pequenos)
JS_MIDIAS_DOM = r'''(root) => {
    const out = [];
    root.querySelectorAll('video').forEach(v => {
        const srcs = [v.currentSrc, v.getAttribute('src')];
        v.querySelectorAll('source').forEach(s => srcs.push(s.getAttribute('src')));
        srcs.forEach(s => { if (s && !s.startsWith('blob:')) out.push({type: 'video', url: s}); });
        const poster = v.getAttribute('poster');
        if (poster && !poster.startsWith('data:')) out.push({type: 'thumb', url: poster});
    });
    root.querySelectorAll('img').forEach(i => {
        const s = i.currentSrc || i.getAttribute('src');
        if (!s || s.startsWith('data:') || s.includes('rsrc.php') || s.includes('profpic')) return;
        const w = Math.max(i.naturalWidth || 0, i.getBoundingClientRect().width);
        if (w && w < 100) return;
        out.push({type: 'image', url: s});
    });
    return out;
}'''

# Força o carregamento dos <video> presentes (mudo, sem som) para que a CDN entregue o .mp4
JS_PLAY_VIDEOS = r'''(root) => {
    root.querySelectorAll('video').forEach(v => { try { v.muted = true; v.play().catch(() => {}); } catch (e) {} });
}'''

# Marca todos os contêineres com rolagem interna dentro do modal
JS_ACHAR_ROLAVEIS = r'''(dialog) => {
    const els = [dialog, ...dialog.querySelectorAll('*')];
    const sc = els.filter(e => {
        const s = getComputedStyle(e);
        return /(auto|scroll|overlay)/.test(s.overflowY) && e.scrollHeight > e.clientHeight + 4;
    });
    sc.forEach((e, i) => e.setAttribute('data-adlib-scroll', String(i)));
    return sc.length;
}'''

JS_ROLAR_TOPO = r'''(dialog) => {
    dialog.querySelectorAll('[data-adlib-scroll]').forEach(e => { e.scrollTop = 0; });
    if (dialog.hasAttribute('data-adlib-scroll')) dialog.scrollTop = 0;
}'''

# Desce um "passo" (80% da altura visível) em cada contêiner; retorna true quando todos chegaram ao fim
JS_ROLAR_PASSO = r'''(dialog) => {
    const els = Array.from(dialog.querySelectorAll('[data-adlib-scroll]'));
    if (dialog.hasAttribute('data-adlib-scroll')) els.push(dialog);
    let todosNoFim = true;
    for (const e of els) {
        const antes = e.scrollTop;
        e.scrollTop = Math.min(e.scrollTop + Math.max(200, e.clientHeight * 0.8), e.scrollHeight);
        e.dispatchEvent(new Event('scroll', {bubbles: true}));
        const fim = e.scrollTop + e.clientHeight >= e.scrollHeight - 2;
        if (!fim && e.scrollTop !== antes) todosNoFim = false;
        if (!fim && e.scrollTop === antes) { /* travou: deixa o fallback de roda do mouse agir */ todosNoFim = false; }
    }
    return {todosNoFim, info: els.map(e => [Math.round(e.scrollTop), e.clientHeight, e.scrollHeight])};
}'''

JS_CENTRO_MAIOR_ROLAVEL = r'''(dialog) => {
    const els = Array.from(dialog.querySelectorAll('[data-adlib-scroll]'));
    if (!els.length) return null;
    els.sort((a, b) => (b.scrollHeight - b.clientHeight) - (a.scrollHeight - a.clientHeight));
    const r = els[0].getBoundingClientRect();
    return {x: r.left + r.width / 2, y: r.top + r.height / 2};
}'''

# Esconde barras fixas/"sticky" do topo (cabeçalho da Ad Library) antes do print do card
JS_ESCONDER_SOBREPOSICOES = r'''(card) => {
    const achados = new Set();
    const xs = [0.05, 0.25, 0.5, 0.75, 0.95].map(f => Math.round(window.innerWidth * f));
    const ys = [2, 30, 60, 100, 140, 180, 220];
    for (const x of xs) for (const y of ys) {
        for (let el of document.elementsFromPoint(x, y)) {
            for (let a = el; a && a !== document.body; a = a.parentElement) {
                if (a.contains(card) || card.contains(a)) continue;
                const pos = getComputedStyle(a).position;
                if ((pos === 'fixed' || pos === 'sticky') && a.getBoundingClientRect().height < window.innerHeight * 0.5) {
                    achados.add(a);
                }
            }
        }
    }
    achados.forEach(a => { a.setAttribute('data-adlib-hidden', a.style.visibility || ''); a.style.visibility = 'hidden'; });
    return achados.size;
}'''

JS_RESTAURAR_SOBREPOSICOES = r'''() => {
    document.querySelectorAll('[data-adlib-hidden]').forEach(a => {
        a.style.visibility = a.getAttribute('data-adlib-hidden');
        a.removeAttribute('data-adlib-hidden');
    });
}'''


# ---------------------------------------------------------------------------
# Coletor principal
# ---------------------------------------------------------------------------

async def run_scraper(target_url=None, debug=False, headless=False):
    print("=====================================================")
    print("          ADLIBHARVEST - META ADS LIBRARY            ")
    print("=====================================================")
    if not target_url:
        target_url = input("Cole a URL COMPLETA da pesquisa na Meta Ads Library: ").strip()
    if not target_url:
        print("URL não fornecida. Encerrando.")
        return

    index = AdIndex()
    estado = {'ad_atual': None, 'videos_rede': {}, 'debug_n': 0, 'debug_dir': None}

    async def on_response(response):
        try:
            url = response.url
            host = urlparse(url).netloc
            ctype = (response.headers.get('content-type') or '').lower()

            # (2) vídeos servidos pela CDN enquanto um modal está aberto
            if 'fbcdn.net' in host and ('video' in ctype or '.mp4' in urlparse(url).path):
                if estado['ad_atual']:
                    estado['videos_rede'].setdefault(estado['ad_atual'], []).append(strip_byte_range(url))
                return

            # (1) JSON da Meta (HTML inicial, GraphQL, endpoints async da Ad Library)
            if 'facebook.com' in host and response.request.resource_type in ('document', 'xhr', 'fetch'):
                if ('graphql' in url or '/ads/library' in url or '/ads/archive' in url
                        or response.request.resource_type == 'document'):
                    text = await response.text()
                    index.feed_text(text)
                    if estado['debug_dir'] and 'ad_archive_id' in text:
                        estado['debug_n'] += 1
                        with open(os.path.join(estado['debug_dir'], f"resp_{estado['debug_n']:04d}.txt"),
                                  'w', encoding='utf-8') as f:
                            f.write(url + '\n\n' + text)
        except Exception:
            pass

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=headless)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            locale="pt-BR",
            viewport={"width": 1920, "height": 1080},
        )
        page = await context.new_page()
        page.on("response", on_response)
        print(f"\nAcessando Alvo: {target_url[:60]}...")

        async def abrir_pagina():
            """Abre a URL e espera os cards aparecerem. O Facebook recarrega a página
            algumas vezes logo após abrir; ler antes disso dá página vazia."""
            await page.goto(target_url, timeout=90000)
            await page.wait_for_load_state('domcontentloaded')
            try:
                await page.wait_for_function(
                    "() => document.body && document.body.innerText.includes('Identificação da biblioteca')",
                    timeout=45000)
            except Exception:
                pass
            await page.wait_for_timeout(3000)
            # Os primeiros anúncios vêm embutidos no HTML inicial, cujo corpo o navegador
            # descarta antes de on_response conseguir lê-lo; por isso lemos do DOM.
            jsons = await page.evaluate('''() => Array.from(document.querySelectorAll('script[type="application/json"]'))
                .map(s => s.textContent).filter(t => t.includes('ad_archive_id'))''')
            for t in jsons:
                index.feed_text(t)
            return jsons

        try:
            html_jsons = await abrir_pagina()
        except Exception as e:
            print(f"Erro inicial ao acessar a pagina: {e}")
            await browser.close()
            return

        # ---------------- Rolagem do feed ----------------
        async def altura_pagina():
            # o Facebook às vezes recarrega a página logo após abrir; espera e tenta de novo
            for _ in range(10):
                try:
                    return await page.evaluate(
                        "(document.scrollingElement || document.documentElement).scrollHeight")
                except Exception:
                    await page.wait_for_load_state('domcontentloaded')
                    await page.wait_for_timeout(2000)
            return 0

        async def rolar_feed():
            last_height = await altura_pagina()
            attempts, scroll_count = 0, 0
            while True:
                scroll_count += 1
                try:
                    await page.evaluate("window.scrollBy(0, 1500)")
                except Exception:
                    pass
                await page.wait_for_timeout(3500)
                new_height = await altura_pagina()
                print(f"-> Scroll #{scroll_count} | Carregando mais anúncios...")
                if new_height == last_height:
                    attempts += 1
                    if attempts >= 3:
                        break
                else:
                    attempts = 0
                    last_height = new_height

        await rolar_feed()
        ad_ids = await page.evaluate(JS_MARCAR_CARDS)
        if not ad_ids:
            print("Nenhum anúncio encontrado na tela; recarregando a página...")
            html_jsons += await abrir_pagina()
            await rolar_feed()
            ad_ids = await page.evaluate(JS_MARCAR_CARDS)

        # Nome da pasta só agora: depois da rolagem o JSON já tem o nome da página
        brand_name = nome_da_marca(target_url, index, await page.title())
        brand_folder = clean_filename(brand_name)
        os.makedirs(brand_folder, exist_ok=True)
        if debug:
            estado['debug_dir'] = os.path.join(brand_folder, '_debug')
            os.makedirs(estado['debug_dir'], exist_ok=True)
            for i, t in enumerate(html_jsons):
                with open(os.path.join(estado['debug_dir'], f"html_{i:02d}.txt"), 'w', encoding='utf-8') as f:
                    f.write(target_url + '\n\n' + t)
        print(f"Pasta da marca criada: {brand_folder}")

        print(f"\nSnapshots JSON capturados: {len(index.ads)}")
        print(f"Anúncios na tela: {len(ad_ids)}")
        print("Iniciando extração profunda com cliques nos modais...")
        extracted_data, log_midias = [], []
        dialog_sel = 'div[role="dialog"]'

        for idx, lib_id in enumerate(ad_ids):
            print(f"Processando Ad: {lib_id} ({idx + 1}/{len(ad_ids)})")
            card = page.locator(f'[data-adlib-id="{lib_id}"]').first
            try:
                await card.scroll_into_view_if_needed()
                await page.wait_for_timeout(500)
            except Exception:
                continue

            snap = index.get(lib_id)

            # ---------- Plataformas (hover nos ícones) ----------
            platforms = {'Facebook': 'Não', 'Instagram': 'Não', 'Audience Network': 'Não',
                         'Messenger': 'Não', 'Threads': 'Não', 'WhatsApp': 'Não'}
            for icon in await card.locator('div[style*="mask-position"]').all():
                try:
                    await icon.scroll_into_view_if_needed()
                    await icon.hover()
                    await page.wait_for_timeout(300)
                    for t in await page.locator('div[role="tooltip"]').all():
                        t_text = await t.inner_text()
                        for nome in platforms:
                            if nome in t_text:
                                platforms[nome] = 'Sim'
                    await page.mouse.move(5, 600)  # tira o mouse de cima, sem clicar em nada
                    await page.wait_for_timeout(100)
                except Exception:
                    pass
            # Se o hover não identificou nada, usa a lista de plataformas do JSON da Meta
            if snap and snap['platforms'] and all(v == 'Não' for v in platforms.values()):
                mapa = {'FACEBOOK': 'Facebook', 'INSTAGRAM': 'Instagram', 'AUDIENCE_NETWORK': 'Audience Network',
                        'MESSENGER': 'Messenger', 'THREADS': 'Threads', 'WHATSAPP': 'WhatsApp'}
                for pf in snap['platforms']:
                    if pf in mapa:
                        platforms[mapa[pf]] = 'Sim'

            # ---------- Metadados do card ----------
            card_text = await card.inner_text()
            status = "Ativo" if re.search(r'(^|\n)\s*Ativo\b', card_text) else "Inativo"
            date_match = re.search(r'Veicula[çc][ãa]o iniciada em\s*([^\n]+)', card_text)
            if not date_match:
                # anúncio inativo: "1 de out de 2026 a 28 de out de 2026" (período completo)
                date_match = re.search(r'(\d{1,2} de \w{3,4}\.? de \d{4}(?:\s*(?:-|–|a)\s*\d{1,2} de \w{3,4}\.? de \d{4})?)',
                                       card_text)
            date = date_match.group(1).strip() if date_match else 'N/A'
            # anúncios recentes trazem "· Tempo total ativo: 20h" na mesma linha: fica só a data
            date = re.split(r'\s*[·•]\s*', date)[0].strip() or 'N/A'
            mult_match = re.search(r'(\d+)\s+anúncios? usa(?:m)? esse criativo', card_text, re.IGNORECASE)
            usa_mult = "Sim" if mult_match else "Não"
            qtd_mult = mult_match.group(1) if mult_match else "1"
            is_dynamic = "Sim" if re.search(r'(produtos dinâmicos|várias versões)', card_text, re.IGNORECASE) else "Não"

            # ---------- Legenda ----------
            safe_copy = clean_caption(snap['body']) if snap and snap['body'] else ''
            if not safe_copy:
                try:
                    safe_copy = clean_caption(await card.evaluate(JS_LEGENDA_DOM))
                except Exception:
                    safe_copy = ''

            ad_folder = os.path.join(brand_folder, lib_id)
            os.makedirs(ad_folder, exist_ok=True)

            # ---------- Abrir modal (SOMENTE "Ver detalhes do anúncio") ----------
            opened = False
            btn = card.get_by_text("Ver detalhes do anúncio", exact=True)
            if await btn.count() > 0:
                estado['ad_atual'] = lib_id
                try:
                    await btn.first.click()
                    await page.locator(dialog_sel).last.wait_for(state='visible', timeout=8000)
                    opened = True
                except Exception:
                    opened = False
            await page.wait_for_timeout(2500 if opened else 300)

            dom_midias = []

            async def coletar_dom(root):
                try:
                    dom_midias.extend(await root.evaluate(JS_MIDIAS_DOM))
                except Exception:
                    pass

            try:
                if opened:
                    modal = page.locator(dialog_sel).last
                    await modal.evaluate(JS_ACHAR_ROLAVEIS)

                    # Topo
                    await modal.evaluate(JS_ROLAR_TOPO)
                    await page.wait_for_timeout(800)
                    await modal.screenshot(path=os.path.join(ad_folder, f"{lib_id}_modal_topo.png"))
                    await modal.evaluate(JS_PLAY_VIDEOS)
                    await coletar_dom(modal)

                    # Carrossel: só botões com rótulo explícito de "próximo" (nunca botões sem texto
                    # genéricos, que podem ser o "X" de fechar ou outros controles).
                    try:
                        nexts = modal.locator(
                            '[aria-label*="róxim" i], [aria-label*="avançar" i], [aria-label*="seguinte" i], '
                            '[aria-label*="next" i]')
                        for k in range(await nexts.count()):
                            nb = nexts.nth(k)
                            aria = (await nb.get_attribute('aria-label') or '').lower()
                            if 'resumo' in aria:
                                continue
                            for _ in range(15):
                                if not await nb.is_visible() or await nb.get_attribute('aria-disabled') == 'true':
                                    break
                                await nb.click(timeout=1500)
                                await page.wait_for_timeout(900)
                                await modal.evaluate(JS_PLAY_VIDEOS)
                                await coletar_dom(modal)
                    except Exception:
                        pass

                    # Rolagem em passos até o fim real do contêiner interno
                    await modal.evaluate(JS_ACHAR_ROLAVEIS)  # recalcula (conteúdo pode ter crescido)
                    parada, ultimo_info = 0, None
                    for passo in range(60):
                        r = await modal.evaluate(JS_ROLAR_PASSO)
                        await page.wait_for_timeout(700)
                        await modal.evaluate(JS_PLAY_VIDEOS)
                        await coletar_dom(modal)
                        if r['info'] == ultimo_info:
                            # scrollTop não mudou via JS: tenta roda do mouse sobre a coluna rolável
                            centro = await modal.evaluate(JS_CENTRO_MAIOR_ROLAVEL)
                            if centro:
                                await page.mouse.move(centro['x'], centro['y'])
                                await page.mouse.wheel(0, 800)
                                await page.wait_for_timeout(700)
                            parada += 1
                        else:
                            parada = 0
                        ultimo_info = r['info']
                        if r['todosNoFim'] or parada >= 3:
                            # confirma que nada novo carregou (lazy loading pode aumentar o scrollHeight)
                            await page.wait_for_timeout(1000)
                            await modal.evaluate(JS_ACHAR_ROLAVEIS)
                            r2 = await modal.evaluate(JS_ROLAR_PASSO)
                            if r2['todosNoFim'] or parada >= 3:
                                break
                    await page.wait_for_timeout(1000)
                    await modal.screenshot(path=os.path.join(ad_folder, f"{lib_id}_modal_base.png"))
                    await coletar_dom(modal)

                    # Fechar modal
                    close_btn = page.locator(f'{dialog_sel} [aria-label="Fechar"], {dialog_sel} i[alt="Fechar"]')
                    if await close_btn.count() > 0:
                        await close_btn.first.click()
                    else:
                        await page.keyboard.press('Escape')
                    try:
                        await page.locator(dialog_sel).first.wait_for(state='hidden', timeout=5000)
                    except Exception:
                        await page.keyboard.press('Escape')
                    await page.wait_for_timeout(800)
                else:
                    # Card sem modal: esconde a barra fixa da Ad Library e centraliza o card
                    await coletar_dom(card)
                    try:
                        await card.evaluate("el => el.scrollIntoView({block: 'center'})")
                        await page.wait_for_timeout(500)
                        await card.evaluate(JS_ESCONDER_SOBREPOSICOES)
                        await page.wait_for_timeout(200)
                        await card.screenshot(path=os.path.join(ad_folder, f"{lib_id}_print_geral.png"))
                    finally:
                        await page.evaluate(JS_RESTAURAR_SOBREPOSICOES)
            except Exception as e:
                print(f"   ! Falha nas capturas de tela: {e}")
            finally:
                estado['ad_atual'] = None

            # ---------- Consolidação de mídias (JSON > rede > DOM) ----------
            await page.wait_for_timeout(300)
            snap = index.get(lib_id) or snap  # o modal pode ter trazido JSON novo
            vistos = set()
            fila = []  # (tipo, url, fonte)

            def add(tipo, url, fonte):
                if not url:
                    return
                k = media_key(url)
                if k in vistos:
                    return
                vistos.add(k)
                fila.append((tipo, url, fonte))

            videos_rede = estado['videos_rede'].pop(lib_id, [])
            if snap and (snap['videos'] or snap['images']):
                # O JSON já lista todas as variações do anúncio. Rede/DOM trariam as mesmas
                # mídias em outra resolução (nome de arquivo diferente), gerando duplicatas.
                for u in snap['videos']:
                    add('video', u, 'json')
                for u in snap['images']:
                    add('image', u, 'json')
            else:
                # Sem JSON: capas de vídeo não são salvas, e imagens só entram se o
                # anúncio não tiver vídeo (senão seriam quadros/capas do próprio vídeo).
                for u in videos_rede:
                    add('video', u, 'rede')
                for m in dom_midias:
                    if m['type'] == 'video':
                        add('video', m['url'], 'dom')
                if not fila:
                    for m in dom_midias:
                        if m['type'] == 'image':
                            add('image', m['url'], 'dom')

            contadores = {'video': 0, 'image': 0, 'thumb': 0}
            prefixo = {'video': 'video', 'image': 'img', 'thumb': 'thumb'}
            ext_padrao = {'video': '.mp4', 'image': '.jpg', 'thumb': '.jpg'}
            for tipo, url, fonte in fila:
                n = contadores[tipo]
                base = os.path.join(ad_folder, f"{lib_id}_{prefixo[tipo]}_{n}")
                salvo = await download_media(context, url, base, ext_padrao[tipo])
                if salvo:
                    contadores[tipo] += 1
                log_midias.append({'Library ID': lib_id, 'Tipo': tipo, 'Fonte': fonte,
                                   'Arquivo': os.path.basename(salvo) if salvo else '', 'Baixado': 'Sim' if salvo else 'Não',
                                   'URL': url})

            tem_video = contadores['video'] > 0 or any(t == 'video' for t, _, _ in fila)
            tem_imagem = contadores['image'] > 0 or any(t == 'image' for t, _, _ in fila)
            # carrossel com cards de vídeo e de imagem vira "Misto"
            midia = "Misto" if tem_video and tem_imagem else ("Vídeo" if tem_video else "Imagem")

            extracted_data.append({
                'Marca': brand_name,
                'Library ID': lib_id,
                'Link Permanente': f"https://www.facebook.com/ads/library/?id={lib_id}",
                'Status': status,
                'Data de Lançamento': date,
                'Tipo de Mídia': midia,
                'Veiculação Facebook': platforms['Facebook'],
                'Veiculação Instagram': platforms['Instagram'],
                'Veiculação Messenger': platforms['Messenger'],
                'Veiculação Audience Network': platforms['Audience Network'],
                'Veiculação Threads': platforms['Threads'],
                'Veiculação WhatsApp': platforms['WhatsApp'],
                'Uso por Múltiplos': usa_mult,
                'Qtd Criativos (A/B)': qtd_mult,
                'É Dinâmico': is_dynamic,
                'Texto da Legenda': safe_copy,
            })
            print(f"   mídias: {contadores['video']} vídeo(s), {contadores['image']} imagem(ns)")

        if extracted_data:
            df = pd.DataFrame(extracted_data)[COLUNAS]
            df.to_excel(os.path.join(brand_folder, f"relatorio_{brand_folder}.xlsx"), index=False)
            if log_midias:
                pd.DataFrame(log_midias).to_csv(os.path.join(brand_folder, f"midias_{brand_folder}.csv"),
                                                index=False, encoding='utf-8-sig')
            print(f"[{brand_name}] Concluído com Sucesso! Relatório salvo em {brand_folder}")

        await browser.close()


def main():
    ap = argparse.ArgumentParser(description="AdLibHarvest - coletor da Meta Ad Library")
    ap.add_argument('--url', help='URL completa da pesquisa na Meta Ad Library')
    ap.add_argument('--debug', action='store_true', help='salva respostas JSON brutas em <marca>/_debug')
    ap.add_argument('--headless', action='store_true', help='executa sem abrir a janela do navegador')
    args = ap.parse_args()
    asyncio.run(run_scraper(args.url, debug=args.debug, headless=args.headless))


if __name__ == "__main__":
    main()
