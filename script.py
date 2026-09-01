import os
import re
import urllib.request
import asyncio
from playwright.async_api import async_playwright
import pandas as pd

def clean_filename(name):
    return re.sub(r'[\\/*?:"<>|]', "", name).strip()

def download_media(url, path):
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=15) as response, open(path, 'wb') as out_file:
            out_file.write(response.read())
    except Exception:
        pass

async def run_scraper():
    print("=====================================================")
    print(" META ADS LIBRARY SCRAPER - VERSÃO FINAL (VALIDAÇÃO) ")
    print("=====================================================")
    target_url = input("Cole a URL COMPLETA da pesquisa na Meta Ads Library: ").strip()
    if not target_url:
        print("URL não fornecida. Encerrando.")
        return

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            locale="pt-BR",
            viewport={"width": 1920, "height": 1080}
        )
        
        page = await context.new_page()
        print(f"\nAcessando Alvo: {target_url[:60]}...")
        
        try:
            await page.goto(target_url, timeout=90000)
            await page.wait_for_load_state('domcontentloaded')
            await page.wait_for_timeout(5000)
            
            title = await page.title()
            brand_name = "Marca_Extraida"
            if "|" in title:
                brand_name = title.split("|")[-1].strip()
            
            brand_folder = clean_filename(brand_name)
            os.makedirs(brand_folder, exist_ok=True)
            print(f"Pasta da marca criada: {brand_folder}")
            
        except Exception as e:
            print(f"Erro inicial ao acessar a pagina: {e}")
            await browser.close()
            return
            
        last_height = await page.evaluate("document.body.scrollHeight")
        attempts = 0
        scroll_count = 0
        while True:
            scroll_count += 1
            await page.evaluate("window.scrollBy(0, 1500)")
            await page.wait_for_timeout(3500)
            
            new_height = await page.evaluate("document.body.scrollHeight")
            print(f"-> Scroll #{scroll_count} | Carregando mais anúncios...")
            if new_height == last_height:
                attempts += 1
                if attempts >= 3:
                    break
            else:
                attempts = 0
                last_height = new_height

        print("\nIniciando extração profunda com cliques nos modais...")
        
        ads_ids_and_locators = await page.evaluate('''() => {
            let res = [];
            let spans = document.querySelectorAll('span');
            for (let span of spans) {
                if (span.innerText.includes('Identificação da biblioteca:')) {
                    let adContainer = span;
                    for(let i=0; i<8; i++) {
                        if(adContainer.parentElement) adContainer = adContainer.parentElement;
                    }
                    if(adContainer.getAttribute('data-test') === 'yes') continue;
                    adContainer.setAttribute('data-test', 'yes');
                    
                    let textContext = adContainer.innerText || '';
                    let match = textContext.match(/Identificação da biblioteca:\\s*(\\d+)/);
                    if(match) {
                        res.push(match[1]);
                    }
                }
            }
            return res;
        }''')
        
        ad_elements = await page.locator('[data-test="yes"]').all()
        extracted_data = []
        
        for idx, lib_id in enumerate(ads_ids_and_locators):
            print(f"Processando Ad: {lib_id} ({idx+1}/{len(ads_ids_and_locators)})")
            card = ad_elements[idx]
            
            try:
                await card.scroll_into_view_if_needed()
                await page.wait_for_timeout(500)
            except:
                continue
            
            # Hover Plataformas (Mouse tracking)
            platforms = {'Facebook': 'Não', 'Instagram': 'Não', 'Audience Network': 'Não', 'Messenger': 'Não', 'Threads': 'Não', 'WhatsApp': 'Não'}
            icons = await card.locator('div[style*="mask-position"]').all()
            for icon in icons:
                try:
                    await icon.scroll_into_view_if_needed()
                    await icon.hover()
                    await page.wait_for_timeout(300)
                    tooltips = await page.locator('div[role="tooltip"]').all()
                    for t in tooltips:
                        t_text = await t.inner_text()
                        if "Facebook" in t_text: platforms['Facebook'] = 'Sim'
                        if "Instagram" in t_text: platforms['Instagram'] = 'Sim'
                        if "Audience Network" in t_text: platforms['Audience Network'] = 'Sim'
                        if "Messenger" in t_text: platforms['Messenger'] = 'Sim'
                        if "Threads" in t_text: platforms['Threads'] = 'Sim'
                        if "WhatsApp" in t_text: platforms['WhatsApp'] = 'Sim'
                    await page.mouse.click(0, 0)
                    await page.wait_for_timeout(100)
                except Exception:
                    pass
            
            card_text = await card.inner_text()
            status = "Ativo" if "Ativo" in card_text else "Inativo"
            date_match = re.search(r'Veiculação iniciada em\s*([A-Za-z0-9\s]+)', card_text)
            date = date_match.group(1).strip() if date_match else 'N/A'
            mult_match = re.search(r'(\d+)\s+anúncios? usam esse criativo', card_text, re.IGNORECASE)
            usa_mult = "Sim" if mult_match else "Não"
            qtd_mult = mult_match.group(1) if mult_match else "1"
            is_dynamic = "Sim" if re.search(r'(produtos dinâmicos|várias versões)', card_text, re.IGNORECASE) else "Não"
            
            # Extração do Botão CTA (Evitando botões do sistema)
            valid_ctas = []
            cta_locators = await card.locator('div[role="button"], a[role="button"]').all()
            for c in cta_locators:
                txt = await c.inner_text()
                txt = txt.split('\n')[0].strip()
                if txt and txt.lower() not in ['ver detalhes do anúncio', 'ver resumo', '']:
                    valid_ctas.append(txt)
            
            final_cta = valid_ctas[-1] if valid_ctas else 'Sem Botão CTA explícito'
            
            if final_cta == 'Sem Botão CTA explícito':
                links = await card.locator('a').all()
                link_ctas = []
                for link in links:
                    href = await link.get_attribute('href') or ''
                    txt = await link.inner_text()
                    txt = txt.split('\n')[0].strip()
                    if href and 'facebook.com' not in href and 'fb.com' not in href and txt:
                        link_ctas.append(txt)
                if link_ctas:
                    final_cta = link_ctas[-1]
            
            # Extração Limpa da Legenda (Direto do Card)
            lines = [l.strip() for l in card_text.split('\n') if l.strip() and l.strip() != '​']
            try:
                sponsor_idx = lines.index('Patrocinado')
                legend_lines = lines[sponsor_idx+1:]
            except:
                legend_lines = lines
                
            clean_legend = []
            for l in legend_lines:
                if re.match(r'^\d+:\d+\s*/\s*\d+:\d+$', l): continue
                if l == final_cta: continue
                lower = l.lower()
                if 'comprar agora' in lower or 'shop now' in lower or 'saiba mais' in lower or 'learn more' in lower or 'aproveite' in lower or lower.startswith('www.'): continue
                if 'curtidas e comentários' in lower: continue
                if 'compartilhar' in lower: continue
                clean_legend.append(l)
            
            safe_copy = " | ".join(clean_legend)[:1500]
            
            # Abrir Modal (Apenas Detalhes do Anúncio)
            btn_texts = ["Ver detalhes do anúncio"]
            opened = False
            for b_txt in btn_texts:
                btn = card.locator(f'text="{b_txt}"')
                if await btn.count() > 0:
                    try:
                        await btn.first.click()
                        opened = True
                        break
                    except:
                        pass
            
            await page.wait_for_timeout(3000)
            
            modal_base = page.locator('div[role="dialog"]')
            if not opened or await modal_base.count() == 0:
                modal = card
            else:
                modal = modal_base.last
            
            media_urls = []
            images = await modal.locator('img').all()
            videos = await modal.locator('video').all()
            for v in videos:
                src = await v.get_attribute('src')
                if src and not src.startswith('blob:'): media_urls.append({'type':'video','url':src})
            for img in images:
                src = await img.get_attribute('src')
                if src and not src.startswith('data:') and 'rsrc.php' not in src and 'profpic' not in src:
                    media_urls.append({'type':'image','url':src})
                    
            midia = "Vídeo" if len(videos) > 0 else "Imagem"
            
            ad_folder = os.path.join(brand_folder, lib_id)
            os.makedirs(ad_folder, exist_ok=True)
            
            # Capturas de Tela
            try:
                if opened:
                    await modal.hover()
                    await page.mouse.wheel(0, -5000)
                    await page.wait_for_timeout(1000)
                    await modal.screenshot(path=os.path.join(ad_folder, f"{lib_id}_modal_topo.png"))
                    
                    await page.mouse.wheel(0, 5000)
                    await page.wait_for_timeout(1000)
                    await modal.screenshot(path=os.path.join(ad_folder, f"{lib_id}_modal_base.png"))
                    
                    close_btn = page.locator('div[aria-label="Fechar"], i[alt="Fechar"]')
                    if await close_btn.count() > 0:
                        await close_btn.first.click()
                    else:
                        await page.keyboard.press('Escape')
                    await page.wait_for_timeout(1000)
                else:
                    await modal.screenshot(path=os.path.join(ad_folder, f"{lib_id}_print_geral.png"))
            except Exception as e:
                pass
            
            # Download de Mídias
            v_count = 0
            i_count = 0
            for m in media_urls:
                if m['type'] == 'video':
                    download_media(m['url'], os.path.join(ad_folder, f"{lib_id}_video_{v_count}.mp4"))
                    v_count += 1
                else:
                    download_media(m['url'], os.path.join(ad_folder, f"{lib_id}_img_{i_count}.jpg"))
                    i_count += 1
            
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
                'Texto do CTA': final_cta
            })

        if extracted_data:
            df = pd.DataFrame(extracted_data)
            colunas = [
                'Marca', 'Library ID', 'Link Permanente', 'Status', 'Data de Lançamento', 'Tipo de Mídia',
                'Veiculação Facebook', 'Veiculação Instagram', 'Veiculação Messenger', 'Veiculação Audience Network',
                'Veiculação Threads', 'Veiculação WhatsApp', 'Uso por Múltiplos', 'Qtd Criativos (A/B)', 'É Dinâmico', 
                'Texto da Legenda', 'Texto do CTA'
            ]
            df = df[colunas]
            df.to_excel(os.path.join(brand_folder, f"relatorio_{brand_name}.xlsx"), index=False)
            print(f"[{brand_name}] Concluído com Sucesso! Relatório salvo em {brand_folder}")
            
        await browser.close()

if __name__ == "__main__":
    asyncio.run(run_scraper())
