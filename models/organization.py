'''
Ce modèle va accueillir les données extraites et nettoyées du champ metrics
'''

from typing import Optional
from sqlmodel import SQLModel, Field

class Organization(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    # Identifiant pivot (ID HAL, ROR ou autre) pour éviter les doublons techniques
    external_id: Optional[str] = Field(default=None, index=True, unique=True) 
    #unique=True sur les external_id => la base refusera techniquement de créer deux fois le même laboratoire ou le même auteur, même si vous les croisez dans des sources différentes
    
    # Nom original et nom nettoyé pour votre analyse
    name: str = Field(index=True)
    clean_name: Optional[str] = Field(default=None, index=True)
    
    # Catégorisation (le cœur de votre sujet : Entreprise vs Académique)
    type: Optional[str] = Field(default=None, index=True) # company, education, facility, archive
    
    # Géographie
    country: Optional[str] = Field(default=None, index=True)
    city: Optional[str] = Field(default=None)