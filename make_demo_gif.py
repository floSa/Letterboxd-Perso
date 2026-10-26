import os
import time
from PIL import Image
from playwright.sync_api import sync_playwright

OUTPUT_DIR = "docs/assets"
GIF_PATH = os.path.join(OUTPUT_DIR, "demo.gif")
os.makedirs(OUTPUT_DIR, exist_ok=True)

frames = []
durations = []

def add_frame(page, duration_ms=650, scale=0.8):
    screenshot_bytes = page.screenshot()
    from io import BytesIO
    img = Image.open(BytesIO(screenshot_bytes))
    if scale != 1.0:
        new_w = int(img.width * scale)
        new_h = int(img.height * scale)
        img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
    frames.append(img.convert("RGB"))
    durations.append(duration_ms)

def run():
    print("--- Lancement de Playwright ---")
    with sync_playwright() as p:
        browser = p.chromium.launch(
            executable_path=r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            headless=True
        )
        # Fenêtre adaptée pour un affichage net (1200 x 750)
        context = browser.new_context(viewport={"width": 1200, "height": 750})
        page = context.new_page()
        
        # Curseur virtuel visuel pour visualiser les clics dans le GIF
        page.add_init_script("""
            window.addEventListener('DOMContentLoaded', () => {
                const cursor = document.createElement('div');
                cursor.id = 'virtual-cursor';
                cursor.style.position = 'fixed';
                cursor.style.width = '22px';
                cursor.style.height = '22px';
                cursor.style.borderRadius = '50%';
                cursor.style.backgroundColor = 'rgba(245, 158, 11, 0.85)';
                cursor.style.border = '2px solid #ffffff';
                cursor.style.boxShadow = '0 0 12px rgba(245, 158, 11, 0.95)';
                cursor.style.pointerEvents = 'none';
                cursor.style.zIndex = '999999';
                cursor.style.transition = 'transform 0.15s ease-out, background-color 0.15s';
                cursor.style.transform = 'translate(-50px, -50px)';
                document.body.appendChild(cursor);

                window.moveCursorTo = (x, y) => {
                    cursor.style.transform = `translate(${x}px, ${y}px)`;
                };
                window.clickCursor = () => {
                    cursor.style.backgroundColor = '#10b981';
                    cursor.style.transform += ' scale(0.85)';
                    setTimeout(() => {
                        cursor.style.backgroundColor = 'rgba(245, 158, 11, 0.85)';
                    }, 250);
                };
            });
        """)

        def move_to(selector, pause=0.25):
            el = page.wait_for_selector(selector)
            box = el.bounding_box()
            if box:
                cx = box["x"] + box["width"] / 2
                cy = box["y"] + box["height"] / 2
                page.evaluate(f"window.moveCursorTo({cx}, {cy});")
                time.sleep(pause)
            return el

        def click_el(selector, pause=0.3):
            el = move_to(selector, pause=0.2)
            page.evaluate("window.clickCursor();")
            el.click()
            time.sleep(pause)

        print("1. Navigation vers Movie Database...")
        page.goto("http://localhost:8080")
        page.wait_for_selector(".movie-row", timeout=10000)
        time.sleep(0.5)

        # Frame 1 : Vue Semaine d'accueil
        print("2. Vue Semaine - Accueil")
        add_frame(page, duration_ms=1200)

        # Défilement vertical pour explorer les sorties de la semaine
        print("3. Défilement vertical semaine...")
        page.evaluate("window.scrollBy({ top: 320, behavior: 'smooth' });")
        time.sleep(0.4)
        add_frame(page, duration_ms=800)
        page.evaluate("window.scrollTo({ top: 0, behavior: 'smooth' });")
        time.sleep(0.4)
        add_frame(page, duration_ms=600)

        # Noter le 1er film 3 étoiles (3.0)
        print("4. Notation 3 étoiles sur le 1er film...")
        star3_selector = ".movie-row:first-child .rating-widget:first-of-type .star-unit:nth-child(3) .click-half.right"
        move_to(star3_selector)
        add_frame(page, duration_ms=500)
        click_el(star3_selector)
        add_frame(page, duration_ms=1000)

        # Noter le 2e film 4 cœurs (4.0)
        print("5. Priorité 4 cœurs sur le 2e film...")
        heart4_selector = ".movie-row:nth-child(2) .rating-widget:nth-of-type(2) .star-unit:nth-child(4) .click-half.right"
        move_to(heart4_selector)
        add_frame(page, duration_ms=500)
        click_el(heart4_selector)
        add_frame(page, duration_ms=1000)

        # Marquer possession (cible verte) sur le 2e film
        print("6. Marquer comme possédé...")
        owned_selector = ".movie-row:nth-child(2) .btn-owned-target"
        move_to(owned_selector)
        click_el(owned_selector)
        add_frame(page, duration_ms=900)

        # Navigation semaine suivante (bouton Suivant ▶)
        print("7. Navigation semaine suivante...")
        click_el("#btn-nav-next")
        time.sleep(0.4)
        add_frame(page, duration_ms=1000)

        # Bascule Vue Mois
        print("8. Bascule en vue Mois...")
        click_el('.scale-btn[data-scale="month"]')
        page.wait_for_selector(".carousel-block", timeout=5000)
        time.sleep(0.4)
        add_frame(page, duration_ms=1100)

        # Défilement horizontal dans le carrousel du mois (clic sur flèche droite ▶)
        print("9. Défilement horizontal carrousel mois...")
        next_btn_selector = ".carousel-block:first-child .btn-carousel-nav.btn-next"
        move_to(next_btn_selector)
        click_el(next_btn_selector)
        time.sleep(0.3)
        add_frame(page, duration_ms=700)
        time.sleep(0.3)
        add_frame(page, duration_ms=1000)

        # Bascule Vue Année
        print("10. Bascule en vue Année...")
        click_el('.scale-btn[data-scale="year"]')
        page.wait_for_selector(".carousel-block", timeout=5000)
        time.sleep(0.5)
        add_frame(page, duration_ms=1100)

        # Défilement horizontal dans un mois de l'année
        print("11. Défilement horizontal carrousel année...")
        move_to(next_btn_selector)
        click_el(next_btn_selector)
        time.sleep(0.3)
        add_frame(page, duration_ms=700)
        time.sleep(0.3)
        add_frame(page, duration_ms=1000)

        # Défilement vertical pour montrer plusieurs mois
        print("12. Défilement vertical année...")
        page.evaluate("window.scrollBy({ top: 380, behavior: 'smooth' });")
        time.sleep(0.4)
        add_frame(page, duration_ms=900)
        page.evaluate("window.scrollTo({ top: 0, behavior: 'smooth' });")
        time.sleep(0.3)
        add_frame(page, duration_ms=600)

        # Onglet Ma Sélection (Watchlist)
        print("13. Onglet Ma Sélection...")
        click_el('.nav-tab[data-tab="watchlist"]')
        time.sleep(0.5)
        add_frame(page, duration_ms=1300)

        # Onglet Films Vus
        print("14. Onglet Films Vus...")
        click_el('.nav-tab[data-tab="watched"]')
        time.sleep(0.5)
        add_frame(page, duration_ms=1300)

        # Retour Sorties Cinéma et Aujourd'hui
        print("15. Retour Sorties Cinéma...")
        click_el('.nav-tab[data-tab="triage"]')
        time.sleep(0.4)
        click_el('#btn-today')
        time.sleep(0.5)
        add_frame(page, duration_ms=1500)

        browser.close()

    print(f"\n--- Total de {len(frames)} frames capturées ---")
    print("Assemblage et optimisation du GIF avec palette adaptative...")
    
    first_frame = frames[0]
    rest_frames = [
        f.quantize(colors=128, method=Image.Resampling.LANCZOS, dither=Image.Dither.FLOYDSTEINBERG)
        for f in frames[1:]
    ]
    first_quantized = first_frame.quantize(colors=128, method=Image.Resampling.LANCZOS, dither=Image.Dither.FLOYDSTEINBERG)

    first_quantized.save(
        GIF_PATH,
        save_all=True,
        append_images=rest_frames,
        duration=durations,
        loop=0,
        optimize=True
    )

    size_mb = os.path.getsize(GIF_PATH) / (1024 * 1024)
    print(f"GIF généré avec succès : {GIF_PATH} ({size_mb:.2f} Mo, {len(frames)} frames)")

if __name__ == "__main__":
    run()
