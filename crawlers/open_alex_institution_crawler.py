"""
    Récupère les organisations via l'endpoint /institutions d'OpenAlex.
    
    Note : Ce crawler est séparé du crawler open_alex_crawler car les structures de données 
    renvoyées par les deux endpoints sont incompatibles (champs, IDs et métadonnées 
    spécifiques aux organisations vs publications).
    """

from pyalex import Institutions, config
import time

config.email = "anthonylazkani.22@gmail.com"

def crawl_openalex_institutions(limit: int = 10):
    """Crawl des institutions OpenAlex avec limite pour test."""
    all_institutions = []
    # On ajoute la limite directement dans la requête API
    query = Institutions().paginate(per_page=min(limit, 200))

    for page in query:
        for inst in page:
            if len(all_institutions) >= limit: break
            
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
        if len(all_institutions) >= limit: break
    
    return all_institutions