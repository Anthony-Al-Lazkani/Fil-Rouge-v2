"""
Gestion des sessions de base de données.
Indispensable pour l'injection de sessions dans vos crawlers ou vos scripts d'import.

Features:
- Initialisation du générateur de session SQLModel.
- Fournit un contexte itérable pour assurer la fermeture automatique des connexions.
"""

from sqlmodel import Session

from database.initialize import engine


def get_session():
    with Session(engine) as session:
        yield session