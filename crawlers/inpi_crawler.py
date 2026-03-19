"""
Crawler INPI / EPO (European Patent Office) spécialisé dans l'innovation IA.

Ce script interroge les services OPS (Open Patent Services) de l'EPO pour extraire 
les brevets mondiaux (via le format DOCDB) répondant à des critères spécifiques.

Limitations Techniques :
- Authentification : Nécessite des identifiants OAuth2 (Consumer Key/Secret) valides (clés dans le .env)
- Throttling : L'API EPO est restrictive, une pause de 1.5s est forcée entre chaque appel
                on peut aller plus vite en s'authentifiant mais on a que 20minutes
- Format : Les données sont récupérées en XML et nécessitent un parsing
  pour extraire les titres, inventeurs et résumés (Abstracts).
- Titre: la plupart des brevets n'ont pas de titres.

Variables de contrôle (reprise dans le pipeline) :
- query : Recherche en langage CQL (ex: 'ti=artificial intelligence' pour le titre).
- max_results : Nombre maximal de brevets à récupérer.
- from_year : Année de priorité/publication minimale pour le filtrage chronologique.

Fonctionnement :
Le script récupère un Token OAuth2, effectue une recherche textuelle, puis pour chaque 
référence trouvée, exécute deux appels supplémentaires pour récupérer les données 
bibliographiques (Biblio) et le résumé (Abstract).
"""

import requests
import base64
import time
import xml.etree.ElementTree as ET


class InpiCrawler:
    """
    Client pour l'API OPS de l'EPO. 
    Gère l'authentification OAuth2, la recherche CQL et le parsing XML des brevets.
    """

    def __init__(self, client_id: str, client_secret: str):
        self.client_id = client_id
        self.client_secret = client_secret
        self.token = None
        self.token_expiry = 0
        self.base_url = "https://ops.epo.org/3.2/rest-services"



    # --- PARTIE TECHNIQUE ---
    
    """
    Gère le cycle de vie du jeton d'accès. 
    Récupère un nouveau token via Basic Auth ou renvoie le token valide en cache.
    """
    def _get_token(self):

        if self.token and time.time() < self.token_expiry:
            return self.token

        auth = base64.b64encode(f"{self.client_id}:{self.client_secret}".encode()).decode()
        headers = {
            "Authorization": f"Basic {auth}",
            "Content-Type": "application/x-www-form-urlencoded",
        }
        r = requests.post(
            "https://ops.epo.org/3.2/auth/accesstoken",
            headers=headers,
            data={"grant_type": "client_credentials"},
        )
        r.raise_for_status()
        payload = r.json()
        self.token = payload["access_token"]
        self.token_expiry = time.time() + int(payload["expires_in"]) - 30
        return self.token





    """
    Génère les entêtes HTTP requis (Bearer Token) pour les requêtes de données.
    Force le format de réponse en XML.
    """
    def _headers(self):
        return {
            "Authorization": f"Bearer {self._get_token()}",
            "Accept": "application/xml",
        }

    # --- PARTIE CRAWLER ---

    def fetch_ai_patents(self, query_text: str = "artificial intelligence", max_results: int = 1500, from_year: int = None):
        results = []
        cql_query = f'ti="{query_text}"'
        if from_year:
            cql_query += f" and pd>={from_year}"

        # On avance par tranches de 100 (limite de l'OEB)
        step = 100
        for start in range(1, max_results + 1, step):
            end = min(start + step - 1, max_results)
            
            print(f"EPO: Requête des brevets {start} à {end}...")
            
            try:
                headers = self._headers()
                headers["X-OPS-Range"] = f"{start}-{end}"

                r = requests.get(
                    f"{self.base_url}/published-data/search",
                    headers=headers,
                    params={"q": cql_query}
                )
                
                if r.status_code == 403:
                    print("EPO: Ban 403 détecté. Pause forcée de 2 minutes...")
                    time.sleep(120)
                    continue # On retente la même tranche
                
                r.raise_for_status()
                refs = self._extract_refs(r.text)
                
                if not refs:
                    print("EPO: Plus de résultats disponibles.")
                    break

                for ref in refs:
                    docdb_id = ref["docdb_id"]
                    
                    # Détails : Biblio
                    r_bib = requests.get(
                        f"{self.base_url}/published-data/publication/docdb/{docdb_id}/biblio",
                        headers=self._headers()
                    )
                    if r_bib.status_code == 200:
                        bib_data = self._parse_biblio(r_bib.text)
                        
                        # Détails : Abstract
                        r_abs = requests.get(
                            f"{self.base_url}/published-data/publication/docdb/{docdb_id}/abstract",
                            headers=self._headers()
                        )
                        abstract = self._parse_abstract(r_abs.text) if r_abs.status_code == 200 else None

                        results.append({
                            "external_id": docdb_id,
                            "title": bib_data["title"],
                            "abstract": abstract,
                            "year": bib_data["year"],
                            "authors": list(set(bib_data["applicants"] + bib_data["inventors"])),
                            "applicants": bib_data["applicants"],
                            "inventors": bib_data["inventors"]
                        })
                        
                        print(f"EPO: {docdb_id} ok.")
                        # Throttling CRITIQUE : 2 secondes entre CHAQUE appel de détail
                        time.sleep(2.0) 
                    
                # Pause supplémentaire entre deux tranches de 100
                print("Fin de tranche, pause de 5 secondes...")
                time.sleep(5.0)

            except Exception as e:
                print(f"Erreur tranche {start}-{end}: {e}")
                break

        return results



    # --- HELPERS PARSING ------------------

    """
    Parse le XML de recherche pour isoler les IDs DOCDB et les numéros de documents.
    Nécessaire pour les appels de détail ultérieurs.
    """
    def _extract_refs(self, xml_text):
        ns = {"ops": "http://ops.epo.org", "ex": "http://www.epo.org/exchange"}
        root = ET.fromstring(xml_text)
        refs = []
        for pub in root.findall(".//ops:publication-reference", ns):
            doc = pub.find("ex:document-id[@document-id-type='docdb']", ns)
            if doc is not None:
                num = doc.findtext("ex:doc-number", namespaces=ns)
                country = doc.findtext("ex:country", namespaces=ns)
                refs.append({"docdb_id": f"{country}{num}", "doc_number": num})
        return refs

    """
    Extrait les métadonnées clés du flux XML bibliographique : 
    Titre (EN), année de publication réelle (YYYY), demandeurs et inventeurs.
    """
    def _parse_biblio(self, xml_text):
        ns = {"ex": "http://www.epo.org/exchange"}
        root = ET.fromstring(xml_text)
        data = {"title": "Untitled Patent", "applicants": [], "inventors": [], "year": None}
        
        # Extraction du titre
        titles = root.findall(".//ex:invention-title[@{http://www.w3.org/XML/1998/namespace}lang='en']", ns)
        if titles: data["title"] = titles[0].text
        
        # Extraction de l'année (Format YYYYMMDD dans le XML)
        pub_date = root.find(".//ex:publication-reference//ex:date", ns)
        if pub_date is not None and pub_date.text:
            try:
                data["year"] = int(pub_date.text[:4]) # On prend les 4 premiers caractères
            except:
                pass

        for a in root.findall(".//ex:applicant//ex:name", ns):
            data["applicants"].append(" ".join(a.text.split()))
        for i in root.findall(".//ex:inventor//ex:name", ns):
            data["inventors"].append(" ".join(i.text.split()))
        return data

    """
    Récupère et concatène les paragraphes textuels du résumé (abstract) du brevet.
    """
    def _parse_abstract(self, xml_text):
        ns = {"ex": "http://www.epo.org/exchange"}
        root = ET.fromstring(xml_text)
        p = root.findall(".//ex:abstract//ex:p", ns)
        return " ".join([node.text for node in p if node.text]) if p else None