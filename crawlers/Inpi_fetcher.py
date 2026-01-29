'''
Module InpiFetcher
==================

Ce module fournit une interface minimale et robuste pour interagir avec l’API
EPO OPS (European Patent Office – Open Patent Services).

Il est utilisé dans le cadre du projet Fil Rouge afin de :
- interroger l’API EPO OPS,
- gérer l’authentification OAuth2 (client credentials),
- récupérer des données brevets structurées au format XML.

Le module est volontairement limité à des responsabilités techniques :
- gestion du token d’accès (récupération, mise en cache, renouvellement),
- construction des en-têtes HTTP,
- appels aux principaux endpoints de l’API.

Aucune logique métier n’est implémentée ici :
- pas de parsing XML,
- pas de stockage des données,
- pas de déduplication ou de consolidation.

Ces traitements sont réalisés dans les scripts de plus haut niveau du pipeline.

Fonctionnalités principales
----------------------------
- Recherche de publications via un critère CQL (endpoint /published-data/search)
- Récupération des métadonnées bibliographiques d’un brevet (endpoint /biblio)
- Récupération du résumé (abstract) d’un brevet (endpoint /abstract)

Le module travaille avec des identifiants de type « docdb », utilisés comme
clé stable pour les appels d’enrichissement.

Ce choix permet d’assurer une séparation claire entre :
- la couche d’accès aux données (API),
- la couche d’analyse et de transformation (scripts du projet Fil Rouge).
'''


import requests
import base64
import time

class InpiFetcher:
    BASE_SEARCH = "https://ops.epo.org/3.2/rest-services/published-data/search"
    BASE_PUBLICATION = "https://ops.epo.org/3.2/rest-services/published-data/publication/epodoc"
    TOKEN_URL = "https://ops.epo.org/3.2/auth/accesstoken"

    def __init__(self, client_id, client_secret):
        self.client_id = client_id
        self.client_secret = client_secret
        self.token = None
        self.token_expiry = 0


    #Ajout des headers pour éviter de tout recopier
    def _headers(self):
        return {
            "Authorization": f"Bearer {self._get_token()}",
            "Accept": "application/xml",
        }


    def _get_token(self):
        if self.token and time.time() < self.token_expiry:
            return self.token

        auth = base64.b64encode(
            f"{self.client_id}:{self.client_secret}".encode()
        ).decode()

        headers = {
            "Authorization": f"Basic {auth}",
            "Content-Type": "application/x-www-form-urlencoded",
        }

        r = requests.post(
            self.TOKEN_URL,
            headers=headers,
            data={"grant_type": "client_credentials"},
        )
        r.raise_for_status()

        payload = r.json()
        self.token = payload["access_token"]
        self.token_expiry = time.time() + int(payload["expires_in"]) - 30
        return self.token

    def search(self, query, start=1, end=25):
        r = requests.get(
            self.BASE_SEARCH,
            headers=self._headers(),
            params={"q": query, "Range": f"{start}-{end}"},
        )
        r.raise_for_status()
        return r.text

    def get_biblio_docdb(self, docdb_id):
        url = f"https://ops.epo.org/3.2/rest-services/published-data/publication/docdb/{docdb_id}/biblio"
        r = requests.get(url, headers=self._headers())
        if r.status_code == 404:
            return None
        r.raise_for_status()
        return r.text
    
    def get_abstract_docdb(self, docdb_id):
        url = f"https://ops.epo.org/3.2/rest-services/published-data/publication/docdb/{docdb_id}/abstract"
        r = requests.get(url, headers=self._headers())
        if r.status_code == 404:
            return None
        r.raise_for_status()
        return r.text