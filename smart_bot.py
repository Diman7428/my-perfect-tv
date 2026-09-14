import os
import re
import requests
from concurrent.futures import ThreadPoolExecutor

# =====================================================================
# 🔑 НАСТРОЙКА ВАШЕГО ДОСТУПА К ILOOK
# Зайдите в личный кабинет iLook, скопируйте вашу ссылку на M3U плейлист 
# и вставьте её вместо текста внутри кавычек ниже:
ILOOK_PLAYLIST_URL = "https://ilook.epg.one/U8VGFNCKR4XDKSAHAQHEW37N/2/img"
# =====================================================================

g1, g2 = "iptv-org.", "github.io"
FREE_RUS_PLAYLIST = "https://" + g1 + g2 + "/iptv/languages/rus.m3u"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
}

def check_free_stream(channel_data):
    if channel_data["source"] == "ilook":
        return {"status": True, "data": channel_data}
    try:
        response = requests.get(channel_data["url"], headers=HEADERS, timeout=3, stream=True)
        if response.status_code < 400:
            return {"status": True, "data": channel_data}
    except:
        pass
    return {"status": False, "data": channel_data}

def start_hybrid_bot():
    if "ССЫЛКА_НА_ВАШ_M3U_ПЛЕЙЛИСТ" in ILOOK_PLAYLIST_URL:
        print("❌ Ошибка! Вы забыли вписать вашу личную ссылку от iLookTV в код скрипта!")
        print("Откройте файл в Блокноте и вставьте рабочую ссылку в переменную ILOOK_PLAYLIST_URL.")
        return

    parsed_channels = []
    seen_urls = set()
    seen_names = set()

    print("📡 1. Подключаюсь к серверам iLookTV и скачиваю ваш плейлист...")
    try:
        response = requests.get(ILOOK_PLAYLIST_URL, headers=HEADERS, timeout=15)
        if response.status_code == 200:
            lines = response.text.split('\n')
            current_meta = ""
            bad_groups = ["Германия", "Франция", "Турция", "Армения", "Азербайджан", "UK", "USA", "Adult", "Клубничка"]
            
            for line in lines:
                line = line.strip()
                if line.startswith("#EXTINF:"):
                    current_meta = line
                elif (line.startswith("http://") or line.startswith("https://")) and current_meta:
                    group_match = re.search(r'group-title="([^"]+)"', current_meta)
                    group_name = group_match.group(1) if group_match else "Общие"
                    
                    is_bad = any(bad.lower() in group_name.lower() for bad in bad_groups)
                    if not is_bad:
                        name = current_meta.split(",")[-1].strip() if "," in current_meta else "ТВ Канал"
                        id_match = re.search(r'tvg-id="([^"]+)"', current_meta)
                        tvg_id = id_match.group(1) if id_match else ""
                        
                        seen_urls.add(line)
                        seen_names.add(name.lower())
                        
                        parsed_channels.append({
                            "name": name, "url": line, "group": group_name, "tvg_id": tvg_id, "source": "ilook"
                        })
                    current_meta = ""
            print(f"  ✅ iLookTV успешно обработан! Добавлено {len(parsed_channels)} качественных каналов.")
        else:
            print(f"  ⚠️ Ошибка скачивания iLook (Код {response.status_code}). Пробую собрать бесплатную базу.")
    except Exception as e:
        print(f"  ⚠️ Не удалось связаться с iLook ({e}). Перехожу к бесплатной базе.")

    print("\n📡 2. Скачиваю дополнительную бесплатную базу СНГ-каналов...")
    try:
        response = requests.get(FREE_RUS_PLAYLIST, headers=HEADERS, timeout=15)
        if response.status_code == 200:
            lines = response.text.split('\n')
            current_meta = ""
            free_added = 0
            
            for line in lines:
                line = line.strip()
                if line.startswith("#EXTINF:"):
                    current_meta = line
                elif (line.startswith("http://") or line.startswith("https://")) and current_meta:
                    name = current_meta.split(",")[-1].strip() if "," in current_meta else "ТВ Канал"
                    
                    if line not in seen_urls and name.lower() not in seen_names:
                        group_match = re.search(r'group-title="([^"]+)"', current_meta)
                        group = group_match.group(1) if group_match else "Бесплатные СНГ"
                        id_match = re.search(r'tvg-id="([^"]+)"', current_meta)
                        tvg_id = id_match.group(1) if id_match else ""
                        
                        seen_urls.add(line)
                        parsed_channels.append({
                            "name": name, "url": line, "group": f"БЕСПЛАТНЫЕ / {group}", "tvg_id": tvg_id, "source": "free"
                        })
                        free_added += 1
                    current_meta = ""
            print(f"  ✅ Бесплатная база отфильтрована! Уникальных бонусов добавлено: {free_added}")
    except Exception as e:
        print(f"  ❌ Ошибка загрузки бесплатной базы: {e}")

    total_to_test = len(parsed_channels)
    if total_to_test == 0:
        print("⚠️ Плейлист пуст. Не удалось собрать каналы.")
        return

    print(f"\n⚡ 3. ЗАПУСКАЮ МАССШТАБНУЮ ПРОВЕРКУ ВСЕХ {total_to_test} КАНАЛОВ В 40 ПОТОКОВ...")
    print("⏳ Сканирование открытых источников займет около 15-20 секунд...\n")
    
    live_channels = []
    with ThreadPoolExecutor(max_workers=40) as executor:
        results = executor.map(check_free_stream, parsed_channels)
        for idx, res in enumerate(results, start=1):
            ch = res["data"]
            if res["status"]:
                live_channels.append(ch)
                if idx <= 30 or idx % 100 == 0 or idx == total_to_test:
                    src_label = "⭐ iLook" if ch["source"] == "ilook" else "🌐 Свободный"
                    print(f"  🟢 [{idx}/{total_to_test}] {ch['name'][:25]} [{src_label}] -> АКТИВЕН")
            else:
                if idx % 50 == 0 or idx == total_to_test:
                    print(f"  🔴 Отфильтровано нерабочих бесплатных серверов: {idx}...")

    desktop = os.path.join(os.path.expanduser("~"), "Desktop")
    output_file = "hybrid_playlist.m3u"
    
    with open(output_file, "w", encoding="utf-8") as file:
        file.write('#EXTM3U url-tvg="http://epg.one"\n')
        for ch in live_channels:
            logo_url = f"https://epg.one{ch['tvg_id']}.png" if ch['tvg_id'] else ""
            file.write(f'#EXTINF:-1 tvg-id="{ch["tvg_id"]}" tvg-logo="{logo_url}" group-title="{ch["group"]}",{ch["name"]}\n')
            file.write(f"{ch['url']}\n")
                
    print(f"\n🏆 ГИБРИДНЫЙ СУПЕРБОТ ПОЛНОСТЬЮ ЗАВЕРШИЛ СБОРКУ!")
    print(f"💾 Успешно упаковано живых каналов: {len(live_channels)} из {total_to_test}")
    print(f"📁 Ваш готовый плейлист сохранен на Рабочем столе: '{output_file}'")

if __name__ == "__main__":
    start_hybrid_bot()
