import re

def remove_truncated_names(input_file, output_file):
    # Regex : 
    # 1. On cherche ce qui est entre guillemets (les colonnes Founders ou Investors)
    # 2. On identifie un segment qui contient "..."
    # 3. On supprime ce segment et le point-virgule qui l'entoure
    
    # Motif pour supprimer "; Nom ..." ou "Nom ...;" ou "Nom ..." s'il est seul
    # On gère les espaces éventuels autour du point-virgule
    pattern = re.compile(r'([^";]+?\.\.\.\s?;?|;?\s?[^";]+?\.\.\.)')

    count = 0
    with open(input_file, 'r', encoding='utf-8') as f_in, \
         open(output_file, 'w', encoding='utf-8') as f_out:
        
        for line in f_in:
            # On ne travaille que sur les parties entre guillemets pour ne pas casser le CSV
            # mais la regex est assez spécifique pour ne pas toucher aux descriptions
            cleaned_line = pattern.sub('', line)
            
            # Nettoyage des doubles points-virgules résiduels ";;" ou "; " en fin de champ
            cleaned_line = cleaned_line.replace('; ;', ';').replace(';;', ';').replace('; "', '"').replace('";', '"')
            
            f_out.write(cleaned_line)
            count += 1

    print(f"Nettoyage des noms tronqués terminé sur {count} lignes.")
    print(f"Fichier propre : {output_file}")

# Utilisation
remove_truncated_names('./data/Crunchbase_csv.csv', 'Crunchbase_final.csv')