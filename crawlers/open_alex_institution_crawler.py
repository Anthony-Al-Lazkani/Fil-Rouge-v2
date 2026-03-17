"""
Récupère les organisations via l'endpoint /institutions d'OpenAlex.

Note : Ce crawler est séparé du crawler open_alex_crawler car les structures de données 
renvoyées par les deux endpoints sont incompatibles (champs, IDs et métadonnées 
spécifiques aux organisations vs publications).

Variables de contrôle :
- limit : Nombre total d'institutions à collecter.
- per_page : Volume de données par appel API (optimisé à 200 pour les institutions).

Fonctionnement :
Le script récupère les métadonnées structurelles incluant le ROR
le type d'entité, la géolocalisation et les statistiques d'influence (works_count, cited_by_count).

Limitations:
Attention, les types sont bien normalisés mais ne correspondent pas forcément au reste (company ou investor)
"""

from pyalex import Institutions, config
import time

config.email = "anthonylazkani.22@gmail.com"

def crawl_openalex_institutions(limit: int = 100):
    """
    Crawl des institutions avec tri par volume de travaux (les plus influentes d'abord).
    limit est piloté depuis le pipeline
    """
    all_institutions = []
    
    # On trie par works_count descendant pour éviter de récupérer des entités vides
    query = (
        Institutions()
        .sort(works_count="desc")
    )

    # per_page est limité à 200 par l'API
    pager = query.paginate(per_page=min(limit, 200))

    for page in pager:
        if len(all_institutions) >= limit:
            break
            
        for inst in page:
            if len(all_institutions) >= limit:
                break
            
            all_institutions.append({
                "external_id": inst.get("id").replace("https://openalex.org/", ""),
                "ror": inst.get("ror"),
                "display_name": inst.get("display_name"),
                "country_code": inst.get("country_code"),
                "type": inst.get("type"),
                "homepage_url": inst.get("homepage_url"),
                "works_count": inst.get("works_count", 0),
                "cited_by_count": inst.get("cited_by_count", 0),
                "acronyms": inst.get("display_name_acronyms", []),
                "raw": inst
            })
            
    print(f"OpenAlex: {len(all_institutions)} institutions collectées.")
    return all_institutions