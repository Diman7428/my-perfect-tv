import os
import re
import urllib.request
import urllib.error

# ==================== НАСТРОЙКИ ====================
TARGET_URLS = [
    "https://p.rapidnas.org/playlist/diman74/22197409/playlist.m3u8",
    "http://cdntv.online/high/bmzasdci3fnx/mpeg.m3u",
    "https://ilook.epg.one/U8VGFNCKR4XDKSAHAQHEW37N/2/img"
]


OUTPUT_PLAYLIST = "combined_playlist.m3u"

# Желаемый порядок групп на выходе
GROUP_ORDER = [
    "Фильмы И Сериалы",
    "СНГ",
    "Другие страны",
    "Общие",
    "Плюсовые",
    "Новостные",
    "Познавательные",
    "Спортивные",
    "Детские",
    "Музыка"
]

# СПИСОК ОЧИЩЕН — каналы не удаляются
IGNORE_KEYWORDS = []

# Точные совпадения для объединения (Регистр НЕ важен — пишем маленькими буквами)
GROUP_REPLACEMENTS = {
    # Объединение кино
    "yosso tv": "Фильмы И Сериалы",
    "kinoint": "Фильмы И Сериалы",
    "кино": "Фильмы И Сериалы",
    "кинозалы": "Фильмы И Сериалы",
    "фильмы и сериалы": "Фильмы И Сериалы",
    "z!": "Фильмы И Сериалы",
    "z": "Фильмы И Сериалы",
    
    # Объединение спорта
    "спорт": "Спортивные",
    "спортивные": "Спортивные",
    
    # Объединение музыки (ошибка исправлена)
    "музыка": "Музыка",
    "музыкальные": "Музыка",
    "musika": "Музыка",

    # Объединение плюсовых каналов
    "плюсовые": "Плюсовые",
    "плюсовые (ru)": "Плюсовые",
    "плюсовые(ru)": "Плюсовые",

    # Объединение в категорию Общие
    "федеральные": "Общие",
    "россия (ru)": "Общие",
    "россия(ru)": "Общие",
    "россия": "Общие"
}

# Поиск стран СНГ (включая Узбекистан)
CIS_KEYWORDS = [
    "беларусь", "belarus", "украина", "ukraine",
    "латвия", "latvia", "lettonia", "литва", "lithuania", "эстония", "estonia", "baltic", "балтия",
    "армения", "armenia", "азербайджан", "azerbaijan", "казахстан", "kazakhstan",
    "туркмения", "туркменистан", "turkmenistan", "узбекистан", "uzbekistan",
    "молдавия", "молдова", "moldova", "грузия", "georgia", "таджикистан", "tajikistan", "киргизия", "kyrgyzstan"
]

# Поиск ВСЕХ остальных зарубежных стран для объединения
WORLD_KEYWORDS = [
    "германия", "germany", "poland", "польша", "turkey", "турция",
    "хорватия", "croatia", "чехия", "czech", "швеция", "sweden",
    "франция", "france", "италия", "italy", "испания", "spain",
    "корея", "korea", "израиль", "israel", "болгария", "bulgaria", "канада", "canada",
    "португалия", "portugal", "румыния", "romania", "словакия", "slovakia",
    "финляндия", "finland", "сша", "usa", "саудовская", "arabia",
    "австралия", "australia", "великобритания", "kingdom", "uk", "дания", "denmark",
    "египет", "egypt", "индия", "india", "нидерланды", "netherlands", "бразилия", "brasil",
    "арабские", "европа", "europe", "afrique", "африка", 
    "норвегия", "norway", "оаэ", "uae"
]
# ===================================================





def download_playlist(url):
    print(f"Скачивание: {url}...")
    try:
        req = urllib.request.Request(
            url, 
            headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        )
        with urllib.request.urlopen(req, timeout=15) as response:
            return response.read().decode('utf-8', errors='ignore')
    except urllib.error.URLError as e:
        print(f"Ошибка сети при скачивании {url}: {e.reason}")
    except Exception as e:
        print(f"Непредвиденная ошибка при обработке {url}: {e}")
    return ""

def parse_m3u_content(content, replacements, cis_keywords, world_keywords, ignore_keywords):
    channels = []
    lines = content.splitlines()

    current_inf = None
    for line in lines:
        line = line.strip()
        if not line:
            continue
        
        if line.startswith("#EXTM3U"):
            continue
            
        if line.startswith("#EXTINF:"):
            current_inf = line
        elif not line.startswith("#") and current_inf:
            group_match = re.search(r'group-title="([^"]+)"', current_inf)
            original_group = group_match.group(1) if group_match else "Без группы"
            
            lookup_key = original_group.strip().lower()
            
            # Шаг 0: Проверка на полное удаление группы
            if any(k in lookup_key for k in ignore_keywords):
                current_inf = None  # Сбрасываем и пропускаем канал
                continue
            
            # Шаг 1: Распределение по оставшимся категориям
            if any(k in lookup_key for k in cis_keywords):
                final_group = "СНГ"
            elif any(k in lookup_key for k in world_keywords):
                final_group = "Другие страны"
            else:
                final_group = replacements.get(lookup_key, original_group.strip())
            
            if final_group != original_group:
                if group_match:
                    current_inf = current_inf.replace(f'group-title="{original_group}"', f'group-title="{final_group}"')
                else:
                    current_inf = current_inf.replace('#EXTINF:', f'#EXTINF: group-title="{final_group}",')
            
            channels.append({
                "inf": current_inf,
                "url": line,
                "group": final_group
            })
            current_inf = None
            
    return channels

def save_combined_playlist(channels, output_path, group_order):
    def sort_key(channel):
        group_name = channel["group"]
        if group_name in group_order:
            return (0, group_order.index(group_name), group_name)
        else:
            return (1, 0, group_name)

    sorted_channels = sorted(channels, key=sort_key)

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write("#EXTM3U\n")
        for ch in sorted_channels:
            f.write(f"{ch['inf']}\n")
            f.write(f"{ch['url']}\n")

def main():
    all_channels = []
    seen_urls = set()

    for url in TARGET_URLS:
        content = download_playlist(url)
        if not content:
            continue
            
        parsed = parse_m3u_content(content, GROUP_REPLACEMENTS, CIS_KEYWORDS, WORLD_KEYWORDS, IGNORE_KEYWORDS)
        print(f"Успешно обработано. Найдено каналов: {len(parsed)}")
        
        for channel in parsed:
            if channel["url"] not in seen_urls:
                seen_urls.add(channel["url"])
                all_channels.append(channel)

    print(f"\nВсего уникальных каналов собрано: {len(all_channels)}")

    if all_channels:
        save_combined_playlist(all_channels, OUTPUT_PLAYLIST, GROUP_ORDER)
        print(f"Результат сохранен в файл: {os.path.abspath(OUTPUT_PLAYLIST)}")
    else:
        print("Не удалось собрать ни одного канала. Файл не перезаписан.")

if __name__ == "__main__":
    main()

    start_hybrid_bot()
