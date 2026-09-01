[README_PT_EN.md](https://github.com/user-attachments/files/31711210/README_PT_EN.md)
# Coletor Automatizado de Anúncios — Meta Ad Library

Ferramenta desenvolvida em Python para coleta automatizada de metadados e mídias de anúncios patrocinados na Biblioteca de Anúncios da Meta (Facebook/Instagram), desenhada com foco em reprodutibilidade científica.

## O que a ferramenta faz
Você entrega o link de uma pesquisa da Biblioteca de Anúncios da Meta, e o robô faz o resto: ele abre a página, rola até o final para garantir o carregamento de todos os anúncios e extrai todos os dados visíveis.

**O resultado final entregue pelo robô será:**
1. Uma **planilha Excel (.xlsx)** contendo 17 variáveis detalhadas de todos os anúncios.
2. Uma **pasta no seu computador** contendo os *prints* (capturas de tela) em tamanho original do anúncio fechado ou detalhado, e todos os vídeos/imagens originais baixados de cada variação contida nele, salvos com a ID oficial para facilitar a indexação na sua pesquisa. Em casos de Anúncios Dinâmicos (DCO), o robô é capaz de emular um clique humano e abrir os Detalhes do Anúncio para baixar todas as mídias subjacentes.

## Variáveis extraídas no Excel
| Variável | Descrição |
|---|---|
| Marca | Nome da marca/página anunciante |
| Library ID | Identificador único do anúncio na plataforma |
| Link Permanente | URL direta para visualizar o anúncio |
| Status | Se o anúncio está Ativo ou Inativo |
| Data de Lançamento | Data em que a veiculação foi iniciada |
| Tipo de Mídia | Formato primário detectado (Imagem ou Vídeo) |
| Veiculação nas Plataformas | 6 colunas indicando presença no Facebook, Instagram, Messenger, Audience Network, Threads e WhatsApp |
| Uso por Múltiplos | Indica testes A/B: se o exato mesmo anúncio aparece repetido na interface ("X anúncios usam esse criativo") |
| Qtd Criativos | Número exato de anúncios idênticos rodando sob a mesma ID (Teste A/B) |
| É Dinâmico | Indica presença de Otimização Dinâmica de Criativo (DCO / "Várias versões") utilizando IA |
| Texto da Legenda | A *copy* (texto principal) descrita no anúncio, limpa de botões e HTML |
| Texto do CTA | O que está escrito no botão de clique (ex: "Saiba mais") |

## Como Instalar
**Passo 1: Instalar o Python**
- Acesse python.org/downloads e baixe o Python.
- **MUITO IMPORTANTE:** No Windows, marque **"Add Python to PATH"**.

**Passo 2: Baixar esta ferramenta**
- Baixe os arquivos e coloque-os juntos em uma pasta.

**Passo 3: Instalar as dependências**
- No Terminal/CMD digite: `pip install -r requirements.txt`
- Depois digite: `playwright install`

## Como Usar a Ferramenta
1. Abra o Terminal na pasta.
2. Digite: `python script.py`
3. Cole a URL da pesquisa quando o painel solicitar.
4. Aguarde sem mexer na tela. O sistema irá gerar as subpastas com as capturas e a planilha estruturada ao final.

## Limitações Metodológicas Importantes
- **Agrupamento Dinâmico (DCO):** Se a plataforma reportar "~110 anúncios" no contador geral, mas o robô extrair apenas "78", não é um erro. A Meta agrupa sub-variações de uma mesma campanha sob uma matriz na interface visual. O robô coleta estritamente as matrizes independentes físicas (DOM), desduplicando as inflações do back-end.

## Licença
Licença MIT. Consulte o arquivo `LICENSE` para detalhes.

## Como citar
Para utilizar esta ferramenta em trabalhos acadêmicos, por favor, cite nosso artigo metodológico de origem:
[preencher com a referência do artigo, assim que publicado]





# Automated Ad Scraper — Meta Ad Library

A Python-based tool for automated collection of metadata and media from sponsored ads on the Meta Ad Library (Facebook/Instagram), designed with a focus on scientific reproducibility.

## What the tool does
Provide the URL of a Meta Ad Library search, and the robot does the rest: it opens the page, scrolls to the end to ensure all ads are loaded, and extracts all visible data.

**The final output delivered by the robot will be:**
1. An **Excel spreadsheet (.xlsx)** containing 14 detailed variables for all ads.
2. A **local folder** containing screenshots and/or original videos of each ad, saved with the official ID to facilitate indexing in your research.

## Extracted Variables (Excel)
| Variable | Description |
|---|---|
| Brand | Name of the advertising brand/page |
| Library ID | Unique identifier of the ad on the platform |
| Permanent Link | Direct URL to view the ad |
| Status | Whether the ad is Active or Inactive |
| Launch Date | Date the ad started running |
| Media Type | Primary format detected (Image or Video) |
| Platform Placements | 6 columns indicating presence on Facebook, Instagram, Messenger, Audience Network, Threads, and WhatsApp |
| Multiple Use (A/B) | Indicates A/B testing: if the exact same ad is repeated in the interface ("X ads use this creative") |
| Creative Count | Exact number of identical ads running under the same ID (A/B Test) |
| Is Dynamic | Indicates the presence of Dynamic Creative Optimization (DCO / "Multiple versions") using AI |
| Caption Text | The main copy described in the ad, cleaned of buttons and HTML |
| CTA Text | The text on the click button (e.g., "Learn more") |

## How to Install
**Step 1: Install Python**
- Visit python.org/downloads and download Python.
- **VERY IMPORTANT:** On Windows, check the **"Add Python to PATH"** box during installation.

**Step 2: Download this tool**
- Download the repository files and put them in a folder.

**Step 3: Install dependencies**
- In your Terminal/Command Prompt type: `pip install -r requirements.txt`
- Then type: `playwright install`

## How to Use
1. Open the Terminal in the folder.
2. Type: `python script.py`
3. Paste the search URL when prompted.
4. Wait without interacting with the screen. The system will generate subfolders with captures and the structured spreadsheet at the end.

## Important Methodological Limitations
- **Dynamic Grouping (DCO):** If the platform reports "~110 ads" on the general counter, but the robot extracts only "78", this is not an error. Meta groups sub-variations of the same campaign under a root matrix in the visual interface. The robot strictly collects the independent physical matrices (DOM), deduplicating the backend inflations.

## License
MIT License. See the `LICENSE` file for details.

## How to Cite
To use this tool in academic work, please cite our original methodological paper:
[fill in with the article reference, once published]

