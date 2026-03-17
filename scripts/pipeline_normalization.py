import subprocess
import sys

def run_script(script_path, args=None):
    cmd = [sys.executable, script_path]
    if args:
        cmd.extend(args)
    
    print(f"\n>>> EXÉCUTION : {script_path}")
    result = subprocess.run(cmd)
    if result.returncode != 0:
        print(f"!!! ERREUR sur {script_path}")
        return False
    return True

def main():
    print("="*60)
    print("PIPELINE DE NORMALISATION ET RÉCONCILIATION")
    print("="*60)

    # 1. Normalisation des pays
    if not run_script("normalisation/normalisation_country.py"): return

    # 2. Normalisation des auteurs (link_data)
    if not run_script("normalisation/normalisation_link_author_items.py"): return

    # 3. Normalisation des organisations (link_organizations)
    if not run_script("normalisation/normalisation_organizations.py"): return

    # 4. Détection des fondateurs (match_authors_to_founders)
    if not run_script("normalisation/normalisation_founders.py", ["--threshold", "80"]): return

    print("\n" + "="*60)
    print("TOUTES LES ÉTAPES DE NORMALISATION SONT TERMINÉES")
    print("="*60)

if __name__ == "__main__":
    main()