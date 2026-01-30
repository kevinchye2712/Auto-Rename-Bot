import os
import pikepdf
import pdfplumber

# --- CONFIGURATION ---

# 1. The "Big 4" Folders that get the specific "Medical Repricing Revision" suffix
SPECIAL_FOLDERS = [
    "Medical Repricing 2023",
    "Medical Repricing 2024",
    "Medical Repricing Jan 2025",
    "Medical Repricing July 2025"
]

# 2. Titles to IGNORE so names match (Added "MASTER" here)
TITLES = [
    "MR", "MRS", "MS", "MDM", "MADAM", "MISS", "MASTER", 
    "DR", "DOC", "DOCTOR",
    "EN", "ENCIK", "PN", "PUAN", "CIK", "TUAN",
    "HAJI", "HAJJAH", "DATUK", "DATO", "TAN SRI", "AL"
]

def clean_name_strict(name):
    # Standardize name for comparison
    # 1. Upper case
    clean = name.upper()
    # 2. Remove punctuation
    clean = clean.replace('.', ' ').replace(',', ' ')
    # 3. Split and filter out titles
    parts = clean.split()
    filtered = [word for word in parts if word not in TITLES]
    return " ".join(filtered)

def extract_life_assured(pdf_path, password):
    # Decrypt and find the real name inside
    temp_filename = f"temp_{os.path.basename(pdf_path)}"
    try:
        with pikepdf.open(pdf_path, password=password) as pdf:
            pdf.save(temp_filename)
        
        life_assured_name = None
        with pdfplumber.open(temp_filename) as pdf:
            first_page = pdf.pages[0]
            text = first_page.extract_text()
            if text:
                for line in text.split('\n'):
                    if "LIFE ASSURED" in line.upper():
                        parts = line.split(':')
                        if len(parts) > 1:
                            life_assured_name = parts[1].strip()
                            break
        return life_assured_name
    except Exception:
        return None
    finally:
        if os.path.exists(temp_filename):
            try:
                os.remove(temp_filename)
            except:
                pass

def process_recursive(current_path, current_password, current_suffix):
    """
    Recursively processes folders using the Password and Suffix 
    determined at the top level.
    """
    folder_name = os.path.basename(current_path)

    # 1. PROCESS FILES
    files = [f for f in os.listdir(current_path) if f.lower().endswith('.pdf')]
    
    if files:
        print(f"    -> Scanning: {folder_name} ... Suffix: _{current_suffix}")
    
    for filename in files:
        # Skip if already renamed
        if current_suffix in filename: continue

        file_path = os.path.join(current_path, filename)
        
        # A. Clean Filename (Get Policy Holder)
        clean_filename = filename.replace(".pdf", "").replace(".PDF", "")
        # Remove (1) duplicates if they exist from cleanup
        if "(" in clean_filename: clean_filename = clean_filename.split("(")[0].strip()
        # Remove " - ID" if it exists
        if " - " in clean_filename: clean_filename = clean_filename.split(" - ")[0].strip()
        
        policy_holder = clean_filename

        # B. Get Real Name (PDF)
        life_assured_raw = extract_life_assured(file_path, current_password)
        
        if not life_assured_raw:
            print(f"       [!] Skip (Read Error): {filename}")
            continue

        # C. Compare & Rename
        ph_clean = clean_name_strict(policy_holder)
        la_clean = clean_name_strict(life_assured_raw)

        if ph_clean == la_clean:
            # Match (e.g. "John" == "MASTER John")
            new_name = f"{policy_holder}_{current_suffix}.pdf"
        else:
            # Mismatch
            new_name = f"{policy_holder} For {life_assured_raw}_{current_suffix}.pdf"

        new_name = new_name.replace("/", "-").replace(":", "")

        try:
            os.rename(file_path, os.path.join(current_path, new_name))
        except OSError:
            print(f"       [ERR] Rename failed: {filename}")

    # 2. GO DEEPER
    # Pass the SAME password and suffix down to children (Batches)
    try:
        subfolders = [d for d in os.listdir(current_path) if os.path.isdir(os.path.join(current_path, d))]
        for sub in subfolders:
            process_recursive(os.path.join(current_path, sub), current_password, current_suffix)
    except PermissionError:
        pass

def main():
    print("--- 1-AGENT RENAMER (Strict Rules) ---")
    agent_path = input("Paste Path to AGENT Folder: ").replace('"', '').strip()
    
    if not os.path.exists(agent_path):
        print("Folder not found.")
        return

    # Loop through the folders inside the Agent Folder (The Campaigns)
    # This determines the logic (Password & Suffix) for everything inside.
    campaigns = [d for d in os.listdir(agent_path) if os.path.isdir(os.path.join(agent_path, d))]
    
    for campaign in campaigns:
        campaign_path = os.path.join(agent_path, campaign)
        
        # --- RULE CHECK ---
        if campaign in SPECIAL_FOLDERS:
            # Case A: It's one of the Big 4
            suffix = "Medical Repricing Revision"
            print(f"\n[!] Special Campaign: {campaign}")
        else:
            # Case B: It's anything else (Interim, etc.)
            suffix = campaign
            print(f"\n[i] Standard Campaign: {campaign}")
            
        # Ask Password ONCE per campaign
        password = input(f"    > Enter Password for '{campaign}': ")
        
        if password:
            # Start recursion for this campaign
            process_recursive(campaign_path, password, suffix)

    print("\nAgent Completed.")

if __name__ == "__main__":
    main()