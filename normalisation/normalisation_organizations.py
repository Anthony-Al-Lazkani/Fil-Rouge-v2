import sys, os, re
from pathlib import Path

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlmodel import Session, select
from database import engine
from models import ResearchItem, Entity, Affiliation, Author

ACRONYM_MAP = {
    "MIT": "Massachusetts Institute of Technology",
    "STANFORD": "Stanford University",
    "HARVARD": "Harvard University",
    "OXFORD": "University of Oxford",
    "CAMBRIDGE": "University of Cambridge",
    "ETH": "Swiss Federal Institute of Technology Zurich",
    "EPFL": "Swiss Federal Institute of Technology in Lausanne",
    "INRIA": "French Institute for Research in Computer Science and Automation",
    "CNRS": "National Centre for Scientific Research",
    "CEA": "French Alternative Energies and Atomic Energy Commission",
    "INSERM": "National Institute of Health and Medical Research",
    "UPMC": "Pierre and Marie Curie University",
    "ENS": "École Normale Supérieure",
    "X": "École Polytechnique",
    "CENTRALESUPELEC": "CentraleSupélec",
    "GOOGLE": "Google",
    "META": "Meta Platforms",
    "IBM": "IBM",
    "MSFT": "Microsoft",
    "AMZN": "Amazon",
    "APPLE": "Apple",
    "NVIDIA": "NVIDIA",
    "DEEPSEEK": "DeepSeek",
    "OPENAI": "OpenAI",
    "ANTHROPIC": "Anthropic",
    "BAIDU": "Baidu",
    "ALIBABA": "Alibaba",
    "TENCENT": "Tencent",
}

COMMON_EMAIL_DOMAINS = {
    "mit.edu": "Massachusetts Institute of Technology",
    "stanford.edu": "Stanford University",
    "harvard.edu": "Harvard University",
    "cam.ac.uk": "University of Cambridge",
    "ox.ac.uk": "University of Oxford",
    "eth.ch": "Swiss Federal Institute of Technology Zurich",
    "epfl.ch": "Swiss Federal Institute of Technology in Lausanne",
    "inria.fr": "INRIA",
    "cnrs.fr": "CNRS",
    "cea.fr": "CEA",
    "inserm.fr": "INSERM",
    "polytechnique.edu": "École Polytechnique",
    "ens.psl.eu": "École Normale Supérieure",
    "universite-paris-saclay.fr": "Université Paris-Saclay",
    "sorbonne-universite.fr": "Sorbonne University",
}


def extract_acronym(name: str) -> str:
    """Extract acronym from name (e.g., 'Massachusetts Institute of Technology' -> 'MIT')."""
    if not name:
        return ""
    words = name.upper().split()
    if len(words) <= 1:
        return ""
    result = "".join(w[0] for w in words if w and w[0].isupper() and len(w) > 1)
    return result if len(result) >= 2 else ""


def normalize_org_name(name: str) -> str:
    """Normalize organization name for comparison."""
    if not name:
        return ""
    name = name.upper().strip()
    name = re.sub(r"[,.\-–—:()]+", " ", name)
    name = " ".join(name.split())
    return name


def run_org_linker():
    BLACKLIST = {
        "BENCHMARK",
        "AI",
        "LAB",
        "BUSINESS",
        "FIGURE",
        "TRAINING",
        "IMPACT",
        "SCIENCE",
        "LABORATORY",
        "RESEARCH",
        "INSTITUTE",
        "UNIVERSITY",
        "DEPARTMENT",
    }

    print("=== LIAISON DES ORGANISATIONS (MODE RÉCUPÉRATION CIBLÉE) ===")
    stats = {"ror": 0, "email": 0, "name": 0, "acronym": 0, "text": 0}

    with Session(engine) as session:
        all_entities = session.exec(select(Entity)).all()

        ror_map = {e.ror: e.id for e in all_entities if e.ror}
        name_map = {}
        acronym_map = {}
        domain_map = {}

        for e in all_entities:
            name_up = normalize_org_name(e.name)
            if name_up and name_up not in BLACKLIST:
                name_map[name_up] = e.id

                acronym = extract_acronym(e.name)
                if acronym and acronym not in acronym_map:
                    acronym_map[acronym] = e.id

            domain = e.raw.get("_email_domain") if e.raw else None
            if domain:
                domain_map[domain.lower()] = e.id

        for domain, org_name in COMMON_EMAIL_DOMAINS.items():
            if domain not in domain_map:
                normalized = normalize_org_name(org_name)
                if normalized in name_map:
                    domain_map[domain] = name_map[normalized]

        affiliations = session.exec(
            select(Affiliation).where(Affiliation.entity_id == None)
        ).all()
        updated = 0

        for aff in affiliations:
            item = session.get(ResearchItem, aff.research_item_id)
            if not item or not item.raw:
                continue

            raw = item.raw
            target_entity_id = None
            found_ror = None

            if "authorships" in raw:
                for auth in raw["authorships"]:
                    for inst in auth.get("institutions", []):
                        ror_val = inst.get("ror")
                        target_entity_id = ror_map.get(ror_val)

                        if not target_entity_id:
                            inst_name = normalize_org_name(inst.get("display_name", ""))
                            target_entity_id = name_map.get(inst_name)

                        if not target_entity_id:
                            inst_acronym = extract_acronym(inst.get("display_name", ""))
                            target_entity_id = acronym_map.get(inst_acronym)

                        if target_entity_id:
                            found_ror = ror_val
                            stats["ror"] += 1
                            break
                    if target_entity_id:
                        break

            if not target_entity_id:
                email = raw.get("email") or raw.get("corresponding_author_email")
                if email and "@" in email:
                    domain = email.split("@")[-1].lower()
                    target_entity_id = domain_map.get(domain)
                    if target_entity_id:
                        stats["email"] += 1

            if not target_entity_id and "structName_s" in raw:
                structs = raw["structName_s"]
                if isinstance(structs, str):
                    structs = [structs]
                for s_name in structs:
                    s_norm = normalize_org_name(s_name)
                    target_entity_id = name_map.get(s_norm)
                    if not target_entity_id:
                        s_acronym = extract_acronym(s_name)
                        target_entity_id = acronym_map.get(s_acronym)
                    if target_entity_id:
                        stats["name"] += 1
                        break

            if not target_entity_id:
                search_zones = []

                if "authorships" in raw:
                    for auth in raw["authorships"]:
                        search_zones.append(
                            normalize_org_name(
                                str(auth.get("raw_affiliation_string", ""))
                            )
                        )

                if "structName_s" in raw:
                    search_zones.append(normalize_org_name(str(raw["structName_s"])))

                combined_zones = " ".join(search_zones)

                for name_key, ent_id in name_map.items():
                    if len(name_key) > 4 and name_key in combined_zones:
                        target_entity_id = ent_id
                        stats["text"] += 1
                        break

                if not target_entity_id:
                    for acr, ent_id in acronym_map.items():
                        if acr in combined_zones:
                            target_entity_id = ent_id
                            stats["acronym"] += 1
                            break

            if target_entity_id:
                aff.entity_id = target_entity_id
                aff.entity_ror = found_ror
                session.add(aff)
                updated += 1

        session.commit()
        print(f"=== TERMINÉ : {updated} affiliations enrichies. ===")
        print(
            f"Stats: ROR={stats['ror']}, Email={stats['email']}, Name={stats['name']}, Acronym={stats['acronym']}, Text={stats['text']}"
        )


if __name__ == "__main__":
    run_org_linker()
