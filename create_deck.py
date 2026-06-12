import os
import re
import sqlite3
import json
import zipfile
import tempfile
import shutil
import genanki

# Folders and paths
BASE_DIR = '/home/samusanc/samusanc/anki'
CARDS_FILE = os.path.join(BASE_DIR, 'cards.txt')
AUDIOS_DIR = os.path.join(BASE_DIR, 'audios')
OUTPUT_APKG = os.path.join(BASE_DIR, 'vocabulario_japones.apkg')

# Helper functions for word cleaning
def clean_japanese_word(word):
    word = word.strip()
    word = re.sub(r'\(お\)\s*', 'お', word)
    word = word.replace('(を)', 'を')
    word = word.replace('(な)', '')
    word = re.sub(r'\((tr\.|intr\.)\)', '', word)
    if 'SF' in word:
        word = 'エスエフ'
    if 'スマートフォン (スマホ)' in word:
        word = 'スマートフォン'
    word = word.replace('…', '').replace('...', '')
    return word.strip()

def sanitize_filename(name):
    name = re.sub(r'[<>:"/\\|?*\s]', '_', name)
    name = re.sub(r'_{2,}', '_', name)
    return name.strip('_')

def sanitize_tag(unit):
    tag = unit.strip().replace(' ', '_').replace('(', '').replace(')', '').replace('/', '_')
    return tag

def update_apkg_card_limit(apkg_path, limit=40):
    """Unzip apkg, update default new card limit in sqlite database, and zip back."""
    temp_dir = tempfile.mkdtemp()
    try:
        # 1. Unzip the apkg
        with zipfile.ZipFile(apkg_path, 'r') as zf:
            zf.extractall(temp_dir)
            
        # 2. Modify collection.anki2
        db_path = os.path.join(temp_dir, 'collection.anki2')
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT dconf FROM col;')
        dconf_str = cursor.fetchone()[0]
        dconf = json.loads(dconf_str)
        
        # Update daily limits to 40 in all configs
        for config_id in dconf:
            if 'new' in dconf[config_id]:
                dconf[config_id]['new']['perDay'] = limit
                print(f"Post-processing: Updated daily new cards limit to {limit} for config {config_id}.")
                
        cursor.execute('UPDATE col SET dconf = ?;', (json.dumps(dconf),))
        conn.commit()
        conn.close()
        
        # 3. Zip it back
        with zipfile.ZipFile(apkg_path, 'w', zipfile.ZIP_DEFLATED) as zf:
            for root, dirs, files in os.walk(temp_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, temp_dir)
                    zf.write(file_path, arcname)
        print(f"Post-processing: Successfully wrote changes back to {apkg_path}")
    finally:
        shutil.rmtree(temp_dir)

def main():
    # 1. Define the Anki Model with Two templates (Modalities)
    model_id = 1607392319
    my_model = genanki.Model(
        model_id,
        'Japonés Minna no Nihongo Model (Dos Vías)',
        fields=[
            {'name': 'Kana'},
            {'name': 'Kanji'},
            {'name': 'Español'},
            {'name': 'Audio'},
        ],
        templates=[
            {
                'name': 'Card 1 (Japonés → Español)',
                'qfmt': '''
                    <div class="card-container">
                      <div class="card-type">Japonés → Español</div>
                      <div class="japanese-word">{{Kanji}}</div>
                    </div>
                ''',
                'afmt': '''
                    <div class="card-container">
                      <div class="card-type">Japonés → Español</div>
                      <div class="japanese-word">{{Kanji}}</div>
                      <hr id="answer">
                      <div class="kana-reading">{{Kana}}</div>
                      <div class="meaning">{{Español}}</div>
                      <div class="audio-player">{{Audio}}</div>
                    </div>
                ''',
            },
            {
                'name': 'Card 2 (Español → Japonés)',
                'qfmt': '''
                    <div class="card-container">
                      <div class="card-type">Español → Japonés</div>
                      <div class="meaning-large">{{Español}}</div>
                    </div>
                ''',
                'afmt': '''
                    <div class="card-container">
                      <div class="card-type">Español → Japonés</div>
                      <div class="meaning-large">{{Español}}</div>
                      <hr id="answer">
                      <div class="japanese-word">{{Kanji}}</div>
                      <div class="kana-reading">{{Kana}}</div>
                      <div class="audio-player">{{Audio}}</div>
                    </div>
                ''',
            },
        ],
        css='''
            .card {
              font-family: "Outfit", "Inter", "Helvetica Neue", Helvetica, Arial, "Hiragino Sans", "Hiragino Kaku Gothic ProN", "Yu Gothic", Meiryo, sans-serif;
              text-align: center;
              color: #2c3e50;
              background-color: #f8f9fa;
              padding: 20px;
            }

            .card-container {
              max-width: 450px;
              margin: 0 auto;
              padding: 30px;
              background: white;
              border-radius: 12px;
              box-shadow: 0 4px 15px rgba(0, 0, 0, 0.05);
            }

            .card-type {
              font-size: 12px;
              text-transform: uppercase;
              letter-spacing: 1px;
              color: #bdc3c7;
              margin-bottom: 15px;
            }

            .japanese-word {
              font-size: 42px;
              font-weight: 700;
              color: #1a252f;
              margin-bottom: 10px;
            }

            .meaning-large {
              font-size: 32px;
              font-weight: 600;
              color: #2980b9;
              margin-bottom: 10px;
            }

            .kana-reading {
              font-size: 24px;
              color: #7f8c8d;
              margin-bottom: 15px;
            }

            .meaning {
              font-size: 20px;
              font-weight: 500;
              color: #2980b9;
              margin-bottom: 20px;
            }

            hr {
              border: 0;
              height: 1px;
              background-image: linear-gradient(to right, rgba(0, 0, 0, 0), rgba(0, 0, 0, 0.1), rgba(0, 0, 0, 0));
              margin: 20px 0;
            }
        '''
    )

    # 2. Initialize the Deck
    deck_id = 202606121
    my_deck = genanki.Deck(
        deck_id,
        'Vocabulario Japonés (Minna no Nihongo)'
    )

    # 3. Read and parse cards.txt
    if not os.path.exists(CARDS_FILE):
        print(f"Error: {CARDS_FILE} not found!")
        return

    current_unit = "General"
    media_files = []
    notes_count = 0

    with open(CARDS_FILE, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line.startswith('###'):
                current_unit = line.replace('###', '').strip()
                continue
            
            if line.startswith('|') and '|' in line:
                parts = [p.strip() for p in line.split('|')]
                if len(parts) >= 4:
                    kana = parts[1]
                    kanji = parts[2]
                    espanol = parts[3]
                    
                    if kana.lower() == 'kana' or all(c in '- ' for c in kana):
                        continue
                    
                    cleaned_kana = clean_japanese_word(kana)
                    cleaned_kanji = clean_japanese_word(kanji)
                    
                    if cleaned_kanji == cleaned_kana or not cleaned_kanji:
                        audio_filename = f"{sanitize_filename(cleaned_kana)}.mp3"
                    else:
                        audio_filename = f"{sanitize_filename(cleaned_kana)}_{sanitize_filename(cleaned_kanji)}.mp3"
                    
                    full_audio_path = os.path.join(AUDIOS_DIR, audio_filename)
                    if os.path.exists(full_audio_path):
                        media_files.append(full_audio_path)
                    
                    tag = sanitize_tag(current_unit)
                    note = genanki.Note(
                        model=my_model,
                        fields=[
                            kana,
                            kanji,
                            espanol,
                            f"[sound:{audio_filename}]"
                        ],
                        tags=[tag]
                    )
                    my_deck.add_note(note)
                    notes_count += 1

    print(f"Prepared {notes_count} notes for the deck.")

    # 4. Package the deck
    package = genanki.Package(my_deck)
    package.media_files = media_files
    package.write_to_file(OUTPUT_APKG)
    print(f"Successfully generated Anki Deck Package: {OUTPUT_APKG}")
    
    # 5. Apply SQLite post-processing to update cards limit
    update_apkg_card_limit(OUTPUT_APKG, limit=40)

if __name__ == '__main__':
    main()
