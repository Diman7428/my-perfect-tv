import os
import re
import urllib.request
import urllib.error

# ==================== SETTINGS ====================
TARGET_URLS = [
    "https://p.rapidnas.org/playlist/diman74/22197409/playlist.m3u8",
    "http://cdntv.online/high/bmzasdci3fnx/mpeg.m3u",
    "https://ilook.epg.one/U8VGFNCKR4XDKSAHAQHEW37N/2/img"
]

OUTPUT_PLAYLIST = "hybrid_playlist.m3u"

GROUP_ORDER = [
    "Фильмы И Сериалы", "СНГ", "Другие страны", "Общие",
    "Плюсовые", "Новостные", "Познавательные", "Спортивные", "Детские", "Музыка"
]

IGNORE_KEYWORDS = []

GROUP_REPLACEMENTS = {
    "yosso tv": "Фильмы И Сериалы", "kinoint": "Фильмы И Сериалы",
    "кино": "Фильмы И Сериалы", "кинозалы": "Фильмы И Сериалы",
    "фильмы и сериалы": "Фильмы И Сериалы", "z!": "Фильмы И Сериалы", "z": "Фильмы И Сериалы",
    "спорт": "Спортивные", "спортивные": "Спортивные",
    "музыка": "Музыка", "музыкальные": "Музыка", "musika": "Музыка",
    "плюсовые": "Плюсовые", "плюсовые (ru)": "Плюсовые", "плюсовые(ru)": "Плюсовые",
    "федеральные": "Общие", "россия (ru)": "Общие", "россия(ru)": "Общие", "россия": "Общие"
}

CIS_KEYWORDS = [
    "беларусь", "belarus", "украина", "ukraine", "латвия", "latvia", "lettonia", "литва", "lithuania",
    "эстония", "estonia", "baltic", "балтия", "армения", "armenia", "азербайджан", "azerbaijan",
    "казахстан", "kazakhstan", "туркмения", "туркменистан", "turkmenistan", "узбекистан", "uzbekistan",
    "молдавия", "молдова", "moldova", "грузия", "georgia", "таджикистан", "tajikistan", "киргизия", "kyrgyzstan"
]

WORLD_KEYWORDS = [
    "германия", "germany", "poland", "польша", "turkey", "турция", "хорватия", "croatia", "чехия", "czech",
    "швеция", "sweden", "франция", "france", "италия", "italy", "испания", "spain", "корея", "korea",
    "израиль", "israel", "болгария", "bulgaria", "канада", "canada", "португалия", "portugal", "румыния", "romania",
    "словакия", "slovakia", "финляндия", "finland", "сша", "usa", "саудовская", "arabia", "австралия", "australia",
    "великобритания", "kingdom", "uk", "дания", "denmark", "египет", "egypt", "индия", "india", "нидерланды", "netherlands",
    "бразилия", "brasil", "арабские", "европа", "europe", "afrique", "африка", "норвегия", "norway", "оаэ", "uae"
]
# ===================================================

def download_playlist(url):
    print(f"Downloading: {url}...")
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'})
        with urllib.request.urlopen(req, timeout=15) as response:
            return response.read().decode('utf-8', errors='ignore')
    except Exception as e:
        print(f"Download error: {e}")
    return ""

def parse_m3u_content(content):
    channels = []
    lines = content.splitlines()
    current_inf = None
    for line in lines:
        line = line.strip()
        if not line or line.startswith("#EXTM3U"): continue
        if line.startswith("#EXTINF:"):
            current_inf = line
        elif not line.startswith("#") and current_inf:
            group_match = re.search(r'group-title="([^"]+)"', current_inf)
            original_group = group_match.group(1) if group_match else "Bez группы"
            lookup_key = original_group.strip().lower()
            
            if any(k in lookup_key for k in IGNORE_KEYWORDS):
                current_inf = None
                continue
            if any(k in lookup_key for k in CIS_KEYWORDS): final_group = "СНГ"
            elif any(k in lookup_key for k in WORLD_KEYWORDS): final_group = "Другие страны"
            else: final_group = GROUP_REPLACEMENTS.get(lookup_key, original_group.strip())
            
            if final_group != original_group:
                if group_match: current_inf = current_inf.replace(f'group-title="{original_group}"', f'group-title="{final_group}"')
                else: current_inf = current_inf.replace('#EXTINF:', f'#EXTINF: group-title="{final_group}",')
            
            channels.append({"inf": current_inf, "url": line, "group": final_group})
            current_inf = None
    return channels

def save_playlist(channels):
    def sort_key(channel):
        group_name = channel["group"]
        if group_name in GROUP_ORDER:
            return (0, GROUP_ORDER.index(group_name), group_name)
        return (1, 0, group_name)

    sorted_channels = sorted(channels, key=sort_key)
    m3u_text = "#EXTM3U\n" + "".join(f"{ch['inf']}\n{ch['url']}\n" for ch in sorted_channels)
    
    with open(OUTPUT_PLAYLIST, 'w', encoding='utf-8') as f:
        f.write(m3u_text)
    print(f"Playlist successfully saved to {OUTPUT_PLAYLIST}.")

def start_hybrid_bot():
    all_channels = []
    seen_urls = set()
    for url in TARGET_URLS:
        content = download_playlist(url)
        if not content: continue
        parsed = parse_m3u_content(content)
        print(f"Processed: {len(parsed)} channels.")
        for ch in parsed:
            if ch["url"] not in seen_urls:
                seen_urls.add(ch["url"])
                all_channels.append(ch)

    print(f"\nTotal unique channels collected: {len(all_channels)}")
    if all_channels: save_playlist(all_channels)

if __name__ == "__main__":
    start_hybrid_bot()
