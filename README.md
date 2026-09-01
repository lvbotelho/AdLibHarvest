[README_PT.md](https://github.com/user-attachments/files/31710912/README_PT.md)
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
