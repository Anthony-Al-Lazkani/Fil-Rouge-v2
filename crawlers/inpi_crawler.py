"""
Crawler INPI / EPO fusionné.
Gère l'auth OAuth2, le throttling, la recherche et le parsing XML.
"""
import requests
import base64
import time
import xml.etree.ElementTree as ET

class InpiCrawler:
    def __init__(self, client_id: str, client_secret: str):
        self.client_id = client_id
        self.client_secret = client_secret
        self.token = None
        self.token_expiry = 0
        self.base_url = "https://ops.epo.org/3.2/rest-services"

    # --- PARTIE TECHNIQUE (Ancien Fetcher) ---

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

    def _headers(self):
        return {
            "Authorization": f"Bearer {self._get_token()}",
            "Accept": "application/xml",
        }

    # --- PARTIE CRAWLER (Logique métier) ---

    def fetch_ai_patents(self, query: str = "ti=artificial intelligence", max_results: int = 10):
        results = []
        try:
            # Recherche
            r = requests.get(
                f"{self.base_url}/published-data/search",
                headers=self._headers(),
                params={"q": query, "Range": f"1-{max_results}"},
            )
            r.raise_for_status()
            refs = self._extract_refs(r.text)

            for ref in refs:
                docdb_id = ref["docdb_id"]
                
                # Récupération Biblio
                r_bib = requests.get(
                    f"{self.base_url}/published-data/publication/docdb/{docdb_id}/biblio",
                    headers=self._headers()
                )
                if r_bib.status_code == 404: continue
                r_bib.raise_for_status()
                bib_data = self._parse_biblio(r_bib.text)

                # Récupération Abstract
                r_abs = requests.get(
                    f"{self.base_url}/published-data/publication/docdb/{docdb_id}/abstract",
                    headers=self._headers()
                )
                abstract = self._parse_abstract(r_abs.text) if r_abs.status_code == 200 else None

                results.append({
                    "external_id": docdb_id,
                    "title": bib_data["title"],
                    "abstract": abstract,
                    "year": self._extract_year(ref["doc_number"]),
                    "authors": bib_data["applicants"] + bib_data["inventors"],
                    "applicants": bib_data["applicants"],
                    "inventors": bib_data["inventors"],
                    "raw": {"ref": ref, "bib": bib_data}
                })
                time.sleep(1.5) # Throttling strict imposé par EPO
            
            return results
        except Exception as e:
            print(f"Erreur Crawler INPI: {e}")
            return []

    # --- HELPERS PARSING ---

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

    def _parse_biblio(self, xml_text):
        ns = {"ex": "http://www.epo.org/exchange"}
        root = ET.fromstring(xml_text)
        data = {"title": "Untitled Patent", "applicants": [], "inventors": []}
        titles = root.findall(".//ex:invention-title[@{http://www.w3.org/XML/1998/namespace}lang='en']", ns)
        if titles: data["title"] = titles[0].text
        for a in root.findall(".//ex:applicant//ex:name", ns):
            data["applicants"].append(" ".join(a.text.split()))
        for i in root.findall(".//ex:inventor//ex:name", ns):
            data["inventors"].append(" ".join(i.text.split()))
        return data

    def _parse_abstract(self, xml_text):
        ns = {"ex": "http://www.epo.org/exchange"}
        root = ET.fromstring(xml_text)
        p = root.findall(".//ex:abstract//ex:p", ns)
        return " ".join([node.text for node in p if node.text]) if p else None

    def _extract_year(self, doc_num):
        return int(doc_num[:4]) if doc_num[:4].isdigit() else None