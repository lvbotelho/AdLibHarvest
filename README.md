# AdLibHarvest — Coletor de Anúncios da Meta Ad Library

Ferramenta em Python para coleta automatizada de metadados e mídias de anúncios da Biblioteca de Anúncios da Meta (Facebook/Instagram), pensada para pesquisa acadêmica e reprodutibilidade.

## O que a ferramenta faz
Você informa o link de uma página (ou pesquisa) da Biblioteca de Anúncios da Meta e o robô faz o resto: abre a página, rola até o fim para carregar todos os anúncios, abre os detalhes de cada um e salva os dados e as mídias.

**Resultado, em uma pasta com o nome da marca:**
1. `relatorio_<marca>.xlsx` — planilha com 16 variáveis por anúncio (ver tabela abaixo).
2. `midias_<marca>.csv` — registro de cada mídia baixada: anúncio, tipo (vídeo/imagem), origem, nome do arquivo, se o download funcionou e o link original. Serve para conferência.
3. Uma subpasta por anúncio, nomeada com a Library ID, contendo:
   - **prints** do anúncio: `_modal_topo.png` e `_modal_base.png` (detalhes do anúncio, topo e fim) ou `_print_geral.png` (quando o anúncio não tem detalhes);
   - **vídeos** (`_video_N.mp4`) de todas as versões, quando o anúncio é em vídeo — capas dos vídeos não são salvas;
   - **imagens** (`_img_N.jpg`) de todas as versões, quando o anúncio é em imagem.

Em anúncios com várias versões (Otimização Dinâmica de Criativo / DCO) e carrosséis, a ferramenta lê a lista de versões que a própria Meta envia ao navegador e baixa cada vídeo ou imagem uma única vez, na maior resolução disponível. Num carrossel que mistura vídeo e imagem, cada parte é salva no seu formato.

**Nome da pasta:** é o nome da página anunciante (ex.: `Coca-Cola`). Se o nome não for encontrado, a pasta se chama `Pagina_<ID da página>`; em pesquisas por palavra-chave, recebe o termo pesquisado. Assim, cada marca coletada fica em uma pasta própria.

## Variáveis do Excel
| Coluna | Descrição |
|---|---|
| Marca | Nome da página anunciante |
| Library ID | Identificador único do anúncio na Biblioteca |
| Link Permanente | URL direta para o anúncio |
| Status | Ativo ou Inativo |
| Data de Lançamento | Data (ou período) de veiculação |
| Tipo de Mídia | Vídeo, Imagem ou Misto (carrossel com cards de vídeo e de imagem) |
| Veiculação Facebook / Instagram / Messenger / Audience Network / Threads / WhatsApp | 6 colunas (Sim/Não) com as plataformas em que o anúncio foi veiculado |
| Uso por Múltiplos | Sim/Não: se a interface informa "X anúncios usam esse criativo" |
| Qtd Criativos (A/B) | Quantos anúncios usam o mesmo criativo (1 quando não informado) |
| É Dinâmico | Sim/Não: se o anúncio tem "várias versões" (DCO) ou produtos dinâmicos |
| Texto da Legenda | Texto principal do anúncio, sem botões, links soltos e textos da interface. Em anúncios dinâmicos, é o texto da primeira versão |

## Como instalar
**Passo 1: Instalar o Python** (versão 3.9 ou superior)
- Acesse python.org/downloads e baixe o Python.
- **MUITO IMPORTANTE:** no Windows, marque **"Add Python to PATH"** durante a instalação.

**Passo 2: Baixar esta ferramenta**
- Baixe os arquivos deste repositório e coloque-os juntos em uma pasta.

**Passo 3: Instalar as dependências**
- No Terminal/Prompt de Comando, dentro da pasta, digite: `pip install -r requirements.txt`
- Depois digite: `playwright install chromium`

## Como usar
1. Abra o Terminal na pasta onde você quer que os resultados sejam salvos.
2. Digite `python script.py` (se o script estiver em outra pasta, informe o caminho, ex.: `python C:\ferramentas\script.py`).
3. Cole o link da Biblioteca de Anúncios quando for solicitado. O ideal é o link da página do anunciante, que contém `view_all_page_id=` no endereço.
4. Uma janela do navegador vai abrir e trabalhar sozinha. **Não mexa nela nem a minimize** até aparecer a mensagem "Concluído com Sucesso!". Páginas com centenas de anúncios podem levar algumas horas.
5. Para coletar outra marca, rode o comando de novo com o novo link.

Opções avançadas:
- `python script.py --url "<link>"` — informa o link direto, sem a pergunta.
- `--headless` — roda sem abrir a janela do navegador.
- `--debug` — salva as respostas brutas da Meta em `<marca>/_debug`, para diagnóstico.

## Testes
O repositório inclui testes automatizados das funções que não dependem do navegador (limpeza da legenda, leitura dos dados da Meta, eliminação de mídias duplicadas e nome da pasta). Para rodá-los, na pasta do repositório: `python tests/test_funcoes.py`

## Limitações
- **Agrupamento de anúncios:** o contador geral da Biblioteca pode mostrar mais anúncios do que a ferramenta coleta. A Meta agrupa variações de uma mesma campanha sob um único anúncio na interface; a ferramenta coleta os anúncios exibidos na página, e as variações de cada um são salvas como mídias dentro da pasta do anúncio.
- **Dependência da interface da Meta:** a coleta depende da estrutura atual da Biblioteca de Anúncios. Mudanças feitas pela Meta podem exigir ajustes no script.
- **Idioma:** o navegador é aberto em português (pt-BR), e a leitura dos anúncios depende dos textos da interface nesse idioma.

## Uso responsável
Esta ferramenta foi desenvolvida para fins de pesquisa acadêmica. Quem a utiliza é responsável por respeitar os Termos de Uso da Meta, a legislação aplicável (incluindo a LGPD) e os direitos autorais sobre os anúncios coletados.

## Autores
Laís Vargas Botelho e Guilherme Bertolassi Corrêa.

## Licença
Licença MIT. Consulte o arquivo `LICENSE`.



---



# AdLibHarvest — Meta Ad Library Scraper

A Python tool for automated collection of metadata and media from ads in the Meta Ad Library (Facebook/Instagram), designed for academic research and reproducibility.

## What the tool does
You provide the URL of a Meta Ad Library page (or search), and the robot does the rest: it opens the page, scrolls to the end to load all ads, opens each ad's details and saves the data and media.

**Output, in a folder named after the brand:**
1. `relatorio_<brand>.xlsx` — spreadsheet with 16 variables per ad (see table below).
2. `midias_<brand>.csv` — log of every media file downloaded: ad, type (video/image), source, file name, whether the download succeeded and the original URL. Useful for auditing.
3. One subfolder per ad, named with its Library ID, containing:
   - **screenshots** of the ad: `_modal_topo.png` and `_modal_base.png` (ad details, top and bottom) or `_print_geral.png` (when the ad has no details view);
   - **videos** (`_video_N.mp4`) of every version, when the ad is a video ad — video cover images are not saved;
   - **images** (`_img_N.jpg`) of every version, when the ad is an image ad.

For ads with multiple versions (Dynamic Creative Optimization / DCO) and carousels, the tool reads the list of versions that Meta itself sends to the browser and downloads each video or image once, at the highest resolution available. In a carousel mixing video and images, each card is saved in its own format.

**Folder name:** the advertiser page's name (e.g. `Coca-Cola`). If the name cannot be found, the folder is named `Pagina_<page ID>`; for keyword searches, it gets the search term. Each brand therefore gets its own folder.

## Excel variables
Column names are in Portuguese.

| Column | Description |
|---|---|
| Marca | Advertiser page name |
| Library ID | Unique ad identifier in the Library |
| Link Permanente | Direct URL to the ad |
| Status | Active (Ativo) or Inactive (Inativo) |
| Data de Lançamento | Start date (or period) of the ad |
| Tipo de Mídia | Video (Vídeo), Image (Imagem) or Mixed (Misto: carousel with video and image cards) |
| Veiculação Facebook / Instagram / Messenger / Audience Network / Threads / WhatsApp | 6 columns (Sim/Não = Yes/No) with the platforms where the ad ran |
| Uso por Múltiplos | Yes/No: whether the interface shows "X ads use this creative" |
| Qtd Criativos (A/B) | How many ads use the same creative (1 when not shown) |
| É Dinâmico | Yes/No: whether the ad has "multiple versions" (DCO) or dynamic products |
| Texto da Legenda | Main ad text, without buttons, bare links and interface text. For dynamic ads, it is the text of the first version |

## How to install
**Step 1: Install Python** (version 3.9 or later)
- Visit python.org/downloads and download Python.
- **VERY IMPORTANT:** on Windows, check **"Add Python to PATH"** during installation.

**Step 2: Download this tool**
- Download the repository files and put them together in a folder.

**Step 3: Install dependencies**
- In the Terminal/Command Prompt, inside the folder, type: `pip install -r requirements.txt`
- Then type: `playwright install chromium`

## How to use
1. Open the Terminal in the folder where you want the results to be saved.
2. Type `python script.py` (if the script is in another folder, give its path, e.g. `python C:\tools\script.py`).
3. Paste the Ad Library URL when prompted. Ideally use the advertiser page URL, which contains `view_all_page_id=`.
4. A browser window will open and work on its own. **Do not touch or minimize it** until the message "Concluído com Sucesso!" appears. Pages with hundreds of ads may take a few hours.
5. To collect another brand, run the command again with the new URL.

Advanced options:
- `python script.py --url "<url>"` — passes the URL directly, without the prompt.
- `--headless` — runs without opening the browser window.
- `--debug` — saves Meta's raw responses to `<brand>/_debug`, for troubleshooting.

## Tests
The repository includes automated tests for the functions that do not depend on the browser (caption cleaning, parsing of Meta's data, removal of duplicate media and folder naming). To run them, from the repository folder: `python tests/test_funcoes.py`

## Limitations
- **Ad grouping:** the Library's overall counter may show more ads than the tool collects. Meta groups variations of the same campaign under a single ad in the interface; the tool collects the ads shown on the page, and each ad's variations are saved as media inside that ad's folder.
- **Dependence on Meta's interface:** collection depends on the current structure of the Ad Library. Changes made by Meta may require script updates.
- **Language:** the browser opens in Portuguese (pt-BR), and reading the ads relies on interface text in that language.

## Responsible use
This tool was developed for academic research. Users are responsible for complying with Meta's Terms of Use, applicable law (including data protection laws such as Brazil's LGPD) and the copyright of the collected ads.

## Authors
Laís Vargas Botelho and Guilherme Bertolassi Corrêa.

## License
MIT License. See the `LICENSE` file.
