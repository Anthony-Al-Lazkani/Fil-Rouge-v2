"""
Ce modèle va accueillir les données extraites et nettoyées du champ metrics
"""

from typing import Optional, List
from sqlmodel import SQLModel, Field
from sqlalchemy import Column, JSON


class Organization(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    # Source of data (crunchbase, startup-dataset, etc.)
    source: Optional[str] = Field(default=None, index=True)
    # Identifiant pivot (ID HAL, ROR ou autre) pour éviter les doublons techniques
    external_id: Optional[str] = Field(default=None, index=True, unique=True)
    # unique=True sur les external_id => la base refusera techniquement de créer deux fois le même laboratoire ou le même auteur, même si vous les croisez dans des sources différentes

    # Nom original et nom nettoyé pour votre analyse
    name: str = Field(index=True)
    clean_name: Optional[str] = Field(default=None, index=True)

    # Catégorisation (le cœur de votre sujet : Entreprise vs Académique)
    type: Optional[str] = Field(
        default=None, index=True
    )  # company, education, facility, archive

    # Géographie
    country: Optional[str] = Field(default=None, index=True)
    city: Optional[str] = Field(default=None)

    # Startup-specific fields
    description: Optional[str] = None
    founded_date: Optional[str] = None
    industries: Optional[List[str]] = Field(
        default_factory=list, sa_column=Column(JSON)
    )
    operating_status: Optional[str] = None
    number_of_employees: Optional[str] = None
    estimated_revenue: Optional[str] = None
    website: Optional[str] = None

    # Funding info
    total_funding: Optional[float] = None
    last_funding_amount: Optional[float] = None
    last_funding_date: Optional[str] = None
    number_of_funding_rounds: Optional[int] = None
    number_of_investors: Optional[int] = None

    # Success metrics
    valuation: Optional[float] = None
    acquisition_count: Optional[int] = None
    ipo: Optional[bool] = None
    acquired: Optional[bool] = None

    # Founders
    founders: Optional[List[str]] = Field(default_factory=list, sa_column=Column(JSON))
    number_of_founders: Optional[int] = None

    # AI specific
    is_ai_related: Optional[bool] = None
    ai_focus_percent: Optional[int] = None

    # Raw data for reference
    raw: Optional[dict] = Field(default_factory=dict, sa_column=Column(JSON))
