import os
import pikepdf
import pdfplumber

# --- CONFIGURATION ---
SPECIAL_FOLDERS = [
    "Medical Repricing 2023",
    "Medical Repricing 2024",
    "Medical Repricing Jan 2025",
    "Medical Repricing July 2025"
]

TITLES = [
    "MR", "MRS", "MS", "MDM", "MADAM", "MISS", "MASTER", 
    "DR", "DOC", "DOCTOR",
    "EN", "ENCIK", "PN", "PUAN", "CIK", "TUAN",
    "HAJI", "HAJJAH", "DATUK", "DATO", "TAN SRI", "AL"
]

SUFFIX = "Medical Repricing Revision"

def clean_name_strict(name):
    # Remove titles and punctuation for accurate comparison
    clean = name.replace('.', ' ').replace(',', ' ').upper()
    parts = clean.split()
    filtered = [word for word in parts if word not in TITLES]
    return " ".join(filtered)

def extract_life_assured(pdf_path, password):
    # Open PDF and grab the real name
    temp_filename = f"temp_check_{os.path.basename(pdf_path)}"
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

def run_quality_check(campaign_path, password):
    print(f"\nScanning: {os.path.basename(campaign_path)}...")
    
    files_checked = 0
    corrections = 0
    
    for current_dir, dirs, files in os.walk(campaign_path):
        pdf_files = [f for f in files if f.lower().endswith('.pdf')]
        
        for filename in pdf_files:
            file_path = os.path.join(current_dir, filename)
            files_checked += 1
            
            # 1. PARSE CURRENT FILENAME to get Policy Holder (PH)
            # Remove extension and the suffix to isolate the names
            base_name = filename.replace(".pdf", "").replace(".PDF", "")
            base_name = base_name.replace(f"_{SUFFIX}", "") 
            
            # If the file currently has " For ", the PH is the first part
            if " For " in base_name:
                policy_holder = base_name.split(" For ")[0].strip()
            else:
                policy_holder = base_name.strip()
                
            # 2. EXTRACT REAL LIFE ASSURED (LA)
            life_assured_real = extract_life_assured(file_path, password)
            
            if not life_assured_real:
                print(f"   [!] Error reading PDF: {filename}")
                continue
                
            # 3. COMPARE
            ph_clean = clean_name_strict(policy_holder)
            la_clean = clean_name_strict(life_assured_real)
            
            # 4. DETERMINE CORRECT FILENAME
            if ph_clean == la_clean:
                # Same Person -> Format: PH_Suffix
                target_name = f"{policy_holder}_{SUFFIX}.pdf"
            else:
                # Different Person -> Format: PH For LA_Suffix
                target_name = f"{policy_holder} For {life_assured_real}_{SUFFIX}.pdf"
                
            target_name = target_name.replace("/", "-").replace(":", "")

            # 5. FIX IF NEEDED
            if filename != target_name:
                try:
                    os.rename(file_path, os.path.join(current_dir, target_name))
                    print(f"   [FIXED] {filename} \n        -> {target_name}")
                    corrections += 1
                except OSError:
                    print(f"   [ERR] Could not rename {filename}")
    
    print(f"Check complete. {files_checked} files scanned, {corrections} corrections made.")

def main():
    print("--- MEDICAL REPRICING QUALITY CHECK ---")
    agent_path = input("Paste Path to AGENT Folder: ").replace('"', '').strip()
    
    if not os.path.exists(agent_path):
        print("Folder not found.")
        return

    # Look for the special folders
    found_any = False
    folders = [d for d in os.listdir(agent_path) if os.path.isdir(os.path.join(agent_path, d))]
    
    for folder_name in folders:
        if folder_name in SPECIAL_FOLDERS:
            found_any = True
            print(f"\n[!] Special Folder Found: {folder_name}")
            pwd = input(f"    > Enter Password for verification: ")
            
            if pwd:
                full_path = os.path.join(agent_path, folder_name)
                run_quality_check(full_path, pwd)
    
    if not found_any:
        print("\nNo 'Medical Repricing' special folders found in this agent folder.")
    else:
        print("\nAll checks completed.")

if __name__ == "__main__":
    main()