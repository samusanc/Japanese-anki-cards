import os
import re
import genanki

# Folders and paths
BASE_DIR = '/home/samusanc/samusanc/anki'
CARDS_FILE = os.path.join(BASE_DIR, 'cards.txt')
AUDIOS_DIR = os.path.join(BASE_DIR, 'audios')
OUTPUT_APKG = os.path.join(BASE_DIR, 'vocabulario_japones_kana.apkg')

# Helper functions for word cleaning (same logic as clean_and_generate.py)
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

def main():
    # 1. Define the Anki Model (Solo Kana)
    model_id = 1607392320
    my_model = genanki.Model(
        model_id,
        'Japonés Solo Kana Model',
        fields=[
            {'name': 'Kana'},
            {'name': 'Español'},
            {'name': 'Audio'},
        ],
        templates=[
            {
                'name': 'Card 1 (Reconocimiento Kana)',
                'qfmt': '''
                    <div class="card-container">
                      <div class="japanese-word">{{Kana}}</div>
                    </div>
                ''',
                'afmt': '''
                    <div class="card-container">
                      <div class="japanese-word">{{Kana}}</div>
                      <hr id="answer">
                      <div class="meaning">{{Español}}</div>
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

            .japanese-word {
              font-size: 42px;
              font-weight: 700;
              color: #1a252f;
              margin-bottom: 10px;
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

    # 2. Initialize the Deck (Solo Kana)
    deck_id = 202606122
    my_deck = genanki.Deck(
        deck_id,
        'Vocabulario Japonés (Solo Kana)'
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
                    
                    # Get correct audio filename based on the existing files
                    cleaned_kana = clean_japanese_word(kana)
                    cleaned_kanji = clean_japanese_word(kanji)
                    
                    if cleaned_kanji == cleaned_kana or not cleaned_kanji:
                        audio_filename = f"{sanitize_filename(cleaned_kana)}.mp3"
                    else:
                        audio_filename = f"{sanitize_filename(cleaned_kana)}_{sanitize_filename(cleaned_kanji)}.mp3"
                    
                    full_audio_path = os.path.join(AUDIOS_DIR, audio_filename)
                    
                    if os.path.exists(full_audio_path):
                        media_files.append(full_audio_path)
                    else:
                        print(f"Warning: Audio file not found for {kana} | {kanji} (expected: {audio_filename})")
                    
                    # Create note (Kana, Español, Audio)
                    tag = sanitize_tag(current_unit)
                    note = genanki.Note(
                        model=my_model,
                        fields=[
                            kana,
                            espanol,
                            f"[sound:{audio_filename}]"
                        ],
                        tags=[tag]
                    )
                    my_deck.add_note(note)
                    notes_count += 1

    print(f"Prepared {notes_count} notes for the Kana deck.")

    # 4. Package the deck
    package = genanki.Package(my_deck)
    package.media_files = media_files
    package.write_to_file(OUTPUT_APKG)
    
    print(f"Successfully generated Kana Anki Deck Package: {OUTPUT_APKG}")
    print(f"Included {len(media_files)} audio files in the package.")

if __name__ == '__main__':
    main()
