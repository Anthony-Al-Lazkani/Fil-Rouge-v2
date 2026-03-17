"""
Domain/Topic Normalization for AI Ecosystem Mapping

This script normalizes topics from research papers and industries from entities
to a unified taxonomy. It also identifies AI-related entities based on topic matching.

Usage:
    python normalisation/normalisation_domain.py
"""

import sys
import os
import re
from pathlib import Path
from collections import defaultdict
from typing import Optional, Set, Dict, List
from functools import lru_cache

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlmodel import Session, select, func
from rapidfuzz import fuzz

from database import engine
from models import ResearchItem, Entity, Affiliation


AI_TAXONOMY = {
    "machine_learning": {
        "keywords": [
            "machine learning",
            "ml",
            "deep learning",
            "neural network",
            "supervised learning",
            "unsupervised learning",
            "reinforcement learning",
        ],
        "display_name": "Machine Learning",
    },
    "nlp": {
        "keywords": [
            "natural language processing",
            "nlp",
            "text mining",
            "text generation",
            "language model",
            "llm",
            "large language model",
            "transformer",
            "bert",
            "gpt",
            "sentiment analysis",
            "machine translation",
            "text classification",
        ],
        "display_name": "Natural Language Processing",
    },
    "computer_vision": {
        "keywords": [
            "computer vision",
            "image recognition",
            "object detection",
            "image segmentation",
            "facial recognition",
            "cnn",
            "convolutional neural",
            "yolo",
            "resnet",
        ],
        "display_name": "Computer Vision",
    },
    "robotics": {
        "keywords": [
            "robotics",
            "robot",
            "autonomous",
            "manipulation",
            "navigation",
            "path planning",
            "motion planning",
            "humanoid",
        ],
        "display_name": "Robotics",
    },
    "ai_ethics": {
        "keywords": [
            "ai ethics",
            "fairness",
            "bias",
            "interpretability",
            "explainable ai",
            "xai",
            "transparency",
            "accountability",
            "responsible ai",
        ],
        "display_name": "AI Ethics & Fairness",
    },
    "generative_ai": {
        "keywords": [
            "generative",
            "gpt",
            "diffusion",
            "gan",
            "generative adversarial",
            "stable diffusion",
            "dalle",
            "midjourney",
            "image generation",
            "text-to-image",
            "text-to-video",
            "sora",
        ],
        "display_name": "Generative AI",
    },
    "reinforcement_learning": {
        "keywords": [
            "reinforcement learning",
            "rl",
            "policy gradient",
            "q-learning",
            "dqn",
            "alphago",
            "multi-agent",
        ],
        "display_name": "Reinforcement Learning",
    },
    "speech": {
        "keywords": [
            "speech",
            "voice",
            "asr",
            "automatic speech recognition",
            "text-to-speech",
            "tts",
            "speaker recognition",
            "voice assistant",
        ],
        "display_name": "Speech Recognition",
    },
    "knowledge_graph": {
        "keywords": [
            "knowledge graph",
            "knowledge base",
            "ontology",
            "rdf",
            "semantic web",
            "entity linking",
            "relation extraction",
        ],
        "display_name": "Knowledge Graphs",
    },
    "edge_ai": {
        "keywords": [
            "edge computing",
            "edge ai",
            "federated learning",
            "on-device",
            "mobile ml",
            "embedded ml",
            "iot",
        ],
        "display_name": "Edge AI",
    },
    "ai_hardware": {
        "keywords": [
            "gpu",
            "tpu",
            "npu",
            "hardware accelerator",
            "ai chip",
            "neuromorphic",
            "quantum computing",
            "quantum machine learning",
        ],
        "display_name": "AI Hardware",
    },
    "autonomous_driving": {
        "keywords": [
            "autonomous driving",
            "self-driving",
            "autonomous vehicle",
            "ad",
            "adas",
            "lane keeping",
            "object detection",
            "scene understanding",
        ],
        "display_name": "Autonomous Driving",
    },
    "medical_ai": {
        "keywords": [
            "medical",
            "healthcare",
            "biomedical",
            "diagnosis",
            "clinical",
            "radiology",
            "pathology",
            "drug discovery",
            "protein",
            "genomics",
        ],
        "display_name": "Medical AI",
    },
    "finance_ai": {
        "keywords": [
            "fintech",
            "financial",
            "trading",
            "fraud detection",
            "credit scoring",
            "blockchain",
            "crypto",
        ],
        "display_name": "Finance AI",
    },
    "nlp_architecture": {
        "keywords": [
            "attention",
            "transformer",
            "encoder",
            "decoder",
            "seq2seq",
            "bert",
            "gpt",
            "t5",
            "llama",
            "mistral",
            "clm",
            "mlm",
        ],
        "display_name": "NLP Architectures",
    },
}


ALIAS_MAP = {
    "artificial intelligence": "machine_learning",
    "ai": "machine_learning",
    "machine-learning": "machine_learning",
    "deep learning": "machine_learning",
    "deeplearning": "machine_learning",
    "neural networks": "machine_learning",
    "neural nets": "machine_learning",
    "natural language processing": "nlp",
    "nlp": "nlp",
    "natural language": "nlp",
    "text mining": "nlp",
    "language model": "nlp",
    "computer vision": "computer_vision",
    "cv": "computer_vision",
    "image processing": "computer_vision",
    "pattern recognition": "computer_vision",
    "robotics": "robotics",
    "robots": "robotics",
    "ethics": "ai_ethics",
    "fairness": "ai_ethics",
    "bias": "ai_ethics",
    "explainable": "ai_ethics",
    "generative ai": "generative_ai",
    "genai": "generative_ai",
    "gan": "generative_ai",
    "diffusion model": "generative_ai",
    "reinforcement learning": "reinforcement_learning",
    "rl": "reinforcement_learning",
    "speech recognition": "speech",
    "voice recognition": "speech",
    "asr": "speech",
    "knowledge graph": "knowledge_graph",
    "knowledge base": "knowledge_graph",
    "ontology": "knowledge_graph",
    "semantic web": "knowledge_graph",
    "edge computing": "edge_ai",
    "edge ml": "edge_ai",
    "federated learning": "edge_ai",
    "iot": "edge_ai",
    "gpu": "ai_hardware",
    "tpu": "ai_hardware",
    "quantum": "ai_hardware",
    "self-driving": "autonomous_driving",
    "autonomous vehicle": "autonomous_driving",
    "autonomous driving": "autonomous_driving",
    "ad": "autonomous_driving",
    "adas": "autonomous_driving",
    "medical ai": "medical_ai",
    "healthcare": "medical_ai",
    "biomedical": "medical_ai",
    "drug discovery": "medical_ai",
    "fintech": "finance_ai",
    "financial technology": "finance_ai",
    "trading": "finance_ai",
    "fraud": "finance_ai",
    "transformer": "nlp_architecture",
    "attention": "nlp_architecture",
    "bert": "nlp_architecture",
    "gpt": "nlp_architecture",
    "llm": "nlp_architecture",
}


@lru_cache(maxsize=5000)
def normalize_topic(topic: str) -> Optional[str]:
    """Normalize a topic to the canonical AI taxonomy key."""
    if not topic:
        return None

    topic_lower = topic.lower().strip()
    topic_clean = re.sub(r"[^\w\s-]", "", topic_lower)
    topic_clean = "-".join(topic_clean.split())

    if topic_clean in ALIAS_MAP:
        return ALIAS_MAP[topic_clean]

    for key, data in AI_TAXONOMY.items():
        for kw in data["keywords"]:
            if kw in topic_lower or topic_lower in kw:
                return key

    return None


def get_canonical_topics(topics: List[str]) -> List[str]:
    """Convert a list of topics to canonical taxonomy keys."""
    canonical = set()
    for topic in topics:
        if topic:
            normalized = normalize_topic(topic)
            if normalized:
                canonical.add(normalized)
    return list(canonical)


def get_display_names(canonical_keys: List[str]) -> List[str]:
    """Get display names for canonical keys."""
    return [
        AI_TAXONOMY.get(key, {}).get("display_name", key.replace("_", " ").title())
        for key in canonical_keys
    ]


def calculate_ai_score(topics: List[str]) -> int:
    """Calculate AI relevance score (0-100) based on topic matching."""
    if not topics:
        return 0

    canonical = get_canonical_topics(topics)
    if not canonical:
        return 0

    return min(100, len(canonical) * 15 + 40)


def normalize_research_topics():
    """Normalize topics in ResearchItem table."""
    print("=== NORMALISATION DES TOPICS DE RECHERCHE ===")

    with Session(engine) as session:
        items = session.exec(select(ResearchItem)).all()
        updated = 0

        for item in items:
            raw_topics = item.topics or []
            if raw_topics:
                canonical = get_canonical_topics(raw_topics)
                display_names = get_display_names(canonical)

                if canonical != raw_topics:
                    item.topics = display_names
                    session.add(item)
                    updated += 1

        session.commit()
        print(f"=== TERMINÉ : {updated} research items mis à jour. ===")


def normalize_entity_industries():
    """Normalize industries in Entity table and calculate AI score."""
    print("=== NORMALISATION DES INDUSTRIES D'ENTITÉS ===")

    stats = {"ai_related": 0, "updated": 0, "total": 0}

    with Session(engine) as session:
        try:
            entities = session.exec(select(Entity)).all()
        except Exception as e:
            print(f"Erreur lors du chargement des entités: {e}")
            print("Skipping entity industry normalization...")
            return

        for entity in entities:
            stats["total"] += 1
            raw_industries = entity.industries or []

            if raw_industries:
                canonical = get_canonical_topics(raw_industries)
                display_names = get_display_names(canonical)

                if canonical != raw_industries:
                    entity.industries = display_names

                ai_score = calculate_ai_score(raw_industries)

                if ai_score >= 50 and entity.is_ai_related != True:
                    entity.is_ai_related = True
                    entity.ai_focus_percent = ai_score
                    stats["ai_related"] += 1

                session.add(entity)
                stats["updated"] += 1

        session.commit()
        print(
            f"=== TERMINÉ : {stats['updated']} entités traitées, {stats['ai_related']} marquées IA ==="
        )


def link_topics_to_entities():
    """Update Entity industries based on linked ResearchItem topics."""
    print("=== LIAISON TOPICS → ENTITÉS ===")

    with Session(engine) as session:
        entities = session.exec(select(Entity)).all()
        updated = 0

        for entity in entities:
            stmt = (
                select(ResearchItem.topics)
                .join(Affiliation, Affiliation.research_item_id == ResearchItem.id)
                .where(Affiliation.entity_id == entity.id)
            )
            topic_results = session.exec(stmt).all()

            all_topics = set()
            for topic_list in topic_results:
                if topic_list:
                    if isinstance(topic_list, list):
                        all_topics.update(t.lower() for t in topic_list if t)
                    elif isinstance(topic_list, str):
                        all_topics.update(t.lower() for t in topic_list.split(",") if t)

            if all_topics:
                canonical = get_canonical_topics(list(all_topics))
                display_names = get_display_names(canonical)

                existing = set(entity.industries or [])
                combined = list(existing | set(display_names))

                entity.industries = combined

                ai_score = calculate_ai_score(list(all_topics))
                if ai_score >= 50:
                    entity.is_ai_related = True
                    entity.ai_focus_percent = max(
                        entity.ai_focus_percent or 0, ai_score
                    )

                session.add(entity)
                updated += 1

        session.commit()
        print(
            f"=== TERMINÉ : {updated} entités enrichies avec les topics des publications. ==="
        )


def print_taxonomy_summary():
    """Print summary of the AI taxonomy coverage."""
    print("\n=== RÉSUMÉ TAXONOMIE IA ===")

    with Session(engine) as session:
        try:
            items = session.exec(select(ResearchItem)).all()
        except Exception as e:
            print(f"Erreur: {e}")
            return

        topic_counts = defaultdict(int)
        for item in items:
            topics = item.topics or []
            for topic in topics:
                normalized = normalize_topic(topic)
                if normalized:
                    topic_counts[normalized] += 1

        print("\nTopics de recherche par catégorie :")
        for key in sorted(
            topic_counts.keys(), key=lambda x: topic_counts[x], reverse=True
        ):
            print(
                f"  {AI_TAXONOMY.get(key, {}).get('display_name', key)}: {topic_counts[key]}"
            )

        try:
            entities = session.exec(
                select(Entity).where(Entity.is_ai_related == True)
            ).all()
            print(f"\nEntités marquées IA: {len(entities)}")
        except:
            print("\n(Entités non disponibles)")


if __name__ == "__main__":
    normalize_research_topics()
    normalize_entity_industries()
    print_taxonomy_summary()
