from deep_translator import GoogleTranslator
import database

def translate_to_german(text):
    """Translates text from any language (auto-detected) to German."""
    # 'auto' detects if you wrote in Turkish, English, etc.
    translator = GoogleTranslator(source='auto', target='de')
    return translator.translate(text)

def process_and_save(text):
    """Handles the translation and saves both versions to the database."""
    print(f"\nOriginal: {text}")
    print("Translating...")
    
    german_translation = translate_to_german(text)
    print(f"Deutsch:  {german_translation}")
    
    database.save_translation(text, german_translation)
    print("✓ Saved to database successfully.")

if __name__ == "__main__":
    # Ensure the database is initialized before doing anything
    database.init_db()
    
    # Testing with your specific example
    test_sentence = "Hello, how are you doing today? I hope everything is going well!"
    process_and_save(test_sentence)