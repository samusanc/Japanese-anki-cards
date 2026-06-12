import os
import re
import asyncio
import edge_tts
import shutil

# Files and folders
BASE_DIR = '/home/samusanc/samusanc/anki'
CARDS_FILE = os.path.join(BASE_DIR, 'cards.txt')
BACKUP_FILE = os.path.join(BASE_DIR, 'cards.txt.bak')
AUDIOS_DIR = os.path.join(BASE_DIR, 'audios')

def clean_japanese_word(word):
    # Remove whitespace
    word = word.strip()
    # Replace (お) or (お) with お
    word = re.sub(r'\(お\)\s*', 'お', word)
    # Replace (を) with を
    word = word.replace('(を)', 'を')
    # Remove (な)
    word = word.replace('(な)', '')
    # Remove (tr.) and (intr.)
    word = re.sub(r'\((tr\.|intr\.)\)', '', word)
    # Handle specific words
    if 'SF' in word:
        word = 'エスエフ'
    if 'スマートフォン (スマホ)' in word:
        word = 'スマートフォン'
    # Remove leading/trailing ellipsis or other symbols
    word = word.replace('…', '').replace('...', '')
    return word.strip()

def sanitize_filename(name):
    # Remove characters that are invalid in filenames
    name = re.sub(r'[<>:"/\\|?*\s]', '_', name)
    # Clean multiple underscores
    name = re.sub(r'_{2,}', '_', name)
    return name.strip('_')

def main():
    # 1. Create a backup of cards.txt
    if os.path.exists(CARDS_FILE):
        shutil.copy2(CARDS_FILE, BACKUP_FILE)
        print(f"Backup created at {BACKUP_FILE}")
    else:
        print(f"Error: {CARDS_FILE} not found!")
        return

    # 2. Parse cards.txt
    sections = []
    current_section = None
    
    with open(CARDS_FILE, 'r', encoding='utf-8') as f:
        for line in f:
            stripped = line.strip()
            # Detect section header
            if stripped.startswith('###'):
                current_section = {
                    'header': stripped,
                    'cards': []
                }
                sections.append(current_section)
                continue
            
            # Detect table row
            if stripped.startswith('|') and '|' in stripped:
                parts = [p.strip() for p in stripped.split('|')]
                if len(parts) >= 4:
                    kana = parts[1]
                    kanji = parts[2]
                    espanol = parts[3]
                    
                    # Ignore header or divider lines
                    if kana.lower() == 'kana' or all(c in '- ' for c in kana):
                        continue
                    
                    if current_section is not None:
                        current_section['cards'].append({
                            'kana': kana,
                            'kanji': kanji,
                            'espanol': espanol
                        })
                    else:
                        # If a card is found before any section header, put it in a general section
                        if not sections:
                            current_section = {'header': '### General', 'cards': []}
                            sections.append(current_section)
                        current_section['cards'].append({
                            'kana': kana,
                            'kanji': kanji,
                            'espanol': espanol
                        })

    print(f"Parsed {len(sections)} sections.")
    
    # 3. Filter duplicates across all sections
    seen = {} # key -> card
    cleaned_sections = []
    
    for section in sections:
        unique_cards = []
        for card in section['cards']:
            # Key is cleaned (kana, kanji) to ensure we detect duplicates correctly
            cleaned_kana = clean_japanese_word(card['kana'])
            cleaned_kanji = clean_japanese_word(card['kanji'])
            key = (cleaned_kana, cleaned_kanji)
            
            if key in seen:
                # Duplicate found!
                # Update the translation if the new one is longer/more descriptive
                existing_card = seen[key]
                if len(card['espanol']) > len(existing_card['espanol']):
                    existing_card['espanol'] = card['espanol']
                print(f"Skipping duplicate: {card['kana']} | {card['kanji']} -> updated translation in original to '{existing_card['espanol']}'")
            else:
                seen[key] = card
                unique_cards.append(card)
        
        if unique_cards:
            cleaned_sections.append({
                'header': section['header'],
                'cards': unique_cards
            })

    # 4. Write cleaned tables back to cards.txt
    with open(CARDS_FILE, 'w', encoding='utf-8') as f:
        for i, section in enumerate(cleaned_sections):
            f.write(f"{section['header']}\n\n")
            f.write("| Kana | Kanji | Español |\n")
            f.write("| --- | --- | --- |\n")
            for card in section['cards']:
                f.write(f"| {card['kana']} | {card['kanji']} | {card['espanol']} |\n")
            # Write separator except for the last section
            if i < len(cleaned_sections) - 1:
                f.write("\n---\n\n")
            else:
                f.write("\n")
                
    print(f"Cleaned cards written to {CARDS_FILE}")

    # 5. Create audios directory
    os.makedirs(AUDIOS_DIR, exist_ok=True)
    print(f"Audios directory prepared at {AUDIOS_DIR}")

    # Prepare TTS tasks
    unique_words_to_generate = []
    for key, card in seen.items():
        cleaned_kana, cleaned_kanji = key
        # Determine filename
        if cleaned_kanji == cleaned_kana or not cleaned_kanji:
            filename = f"{sanitize_filename(cleaned_kana)}.mp3"
        else:
            filename = f"{sanitize_filename(cleaned_kana)}_{sanitize_filename(cleaned_kanji)}.mp3"
        
        unique_words_to_generate.append({
            'text': cleaned_kana,
            'filename': filename,
            'original_kana': card['kana'],
            'original_kanji': card['kanji']
        })

    print(f"Total unique audios to generate: {len(unique_words_to_generate)}")
    
    # 6. Run TTS generation concurrently using asyncio
    async def generate_all():
        sem = asyncio.Semaphore(10) # limit to 10 concurrent requests to be polite and avoid timeouts
        total = len(unique_words_to_generate)
        completed = 0

        async def generate_one(word):
            nonlocal completed
            async with sem:
                filepath = os.path.join(AUDIOS_DIR, word['filename'])
                # Skip if already exists
                if os.path.exists(filepath):
                    completed += 1
                    if completed % 20 == 0 or completed == total:
                        print(f"Progress: {completed}/{total} audios ready.")
                    return
                
                try:
                    communicate = edge_tts.Communicate(word['text'], 'ja-JP-NanamiNeural')
                    await communicate.save(filepath)
                except Exception as e:
                    print(f"Error generating audio for {word['text']}: {e}")
                
                completed += 1
                if completed % 20 == 0 or completed == total:
                    print(f"Progress: {completed}/{total} audios ready.")

        tasks = [generate_one(word) for word in unique_words_to_generate]
        await asyncio.gather(*tasks)

    asyncio.run(generate_all())
    print("All audios generated successfully!")

if __name__ == '__main__':
    main()
