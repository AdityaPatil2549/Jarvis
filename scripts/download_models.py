import os
import whisper

def main():
    print("Downloading Whisper base model (~74MB)...")
    whisper.load_model("base")
    print("Downloading spaCy en_core_web_sm model (~40MB)...")
    os.system("python -m spacy download en_core_web_sm")
    print("Models downloaded successfully.")

if __name__ == "__main__":
    main()
