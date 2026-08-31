#!/usr/bin/env python3
"""Persist conservative visual descriptions for the silent historical Reels."""
from __future__ import annotations

import re
from pathlib import Path

DESCRIPTIONS = {
    "insta_C_OVoncoWLP": "Vêtements streetwear : veste ou hoodie noir richement brodé de grues, fleurs et motifs d'inspiration japonaise.",
    "insta_C1auz7SROxd": "Plan rapproché nocturne d'un kiwi, oiseau brun au long bec, posé sur de l'herbe.",
    "insta_C1NBfhNIAXP": "Démonstration de conception sur tablette avec stylet : un objet ou panneau brun est manipulé dans une interface de modélisation.",
    "insta_C293jpltqQ-": "Gros plan très rapproché sur une montre de luxe ou un détail métallique de cadran.",
    "insta_C3AuqdpNb6m": "Montage sur la création vidéo : appareil photo et objectifs, plan urbain filmé puis timeline de montage avec pistes audio.",
    "insta_C7MTJkeuKTL": "Démonstration artistique : une main peint ou dessine des gouttes d'eau réalistes sur une surface.",
    "insta_C9XmdMzIxUo": "Présentation de t-shirts blancs et beige portant une illustration colorée de personnages de style dessin animé.",
    "insta_Da-GipSEQTW": "Vidéo en arabe à caractère motivationnel ou religieux : homme âgé poussant une charrette dans une rue ancienne.",
    "insta_DAsrlzZuQ8F": "Trois enfants autour d'une grande bouteille verte, dans une petite expérience ou un jeu.",
    "insta_DcgP1woiL-q": "Scène religieuse : homme âgé en tenue blanche et verte devant un groupe de fidèles lors d'un rassemblement.",
    "insta_Dclm0FlRDb8": "Plan cinématique d'une voiture de sport blanche en mouvement, avec gros plan sur la roue arrière.",
    "insta_DQ3-GXHjGL7": "Tutoriel de bricolage : application de mastic ou de joint au pistolet pour réparer des fissures de plafond.",
    "insta_DQLrqUuj4rE": "Réparation de moto : ajustement d'un câble ou d'un levier près du guidon avec une clé plate.",
    "insta_DR73Pnbj6wx": "Moto sportive noire avec pilote casqué, filmée de nuit dans un parking ou une rue urbaine.",
    "insta_DS2sMiwiIqg": "Paysage de montagne spectaculaire : une personne observe une vallée et des sommets sous les nuages.",
    "insta_DU0k8qIDFjz": "Machine de dessin ou plotter utilisant un stylo pour tracer des lignes précises sur une feuille.",
    "insta_DUbJFgCilJK": "Création artistique ou sculpture : oiseau mécanique aux plumes métalliques, tenu ou présenté en intérieur.",
    "insta_DUPVQJnDUC_": "Recette de cuisine : oignons et aromates reviennent dans une poêle avant d'être mélangés à une préparation.",
    "insta_DV-z4ODio5a": "Montage humoristique mêlant réaction d'un homme en maillot de football et foule lors d'un événement ou salon.",
    "insta_DVmqCrOjoCP": "Mème animalier : un oiseau est face à un piège ou un mécanisme improvisé près d'un tas de terre.",
    "insta_DVN7GJGDHrF": "Homme assis face à la caméra, parlant dans un format vlog ou témoignage.",
    "insta_DVQxnnUkxSn": "Montage de scènes religieuses musulmanes avec la mention visible « Imam Tarawih ».",
    "insta_DVtT27JDtvC": "Tutoriel de dessin : main utilisant un feutre bleu pour créer un effet d'eau ou de vagues sur une illustration.",
    "insta_DWAPtuPjAB9": "Mème ou courte scène filmée de près, avec sous-titre anglais sur le fait de se réveiller en retard.",
    "insta_DWMVHx5jehb": "Scène de prière ou de célébration musulmane en Égypte, montrant des personnes sur un balcon.",
    "insta_DWUZ7TUiKNW": "Gros plan mode : chaussure de sport noire et chaussette blanche Nike portée par une personne.",
    "insta_DXCJpbpiUef": "Démonstration pratique dans des toilettes ou une salle de bain, avec un appareil circulaire et du matériel de nettoyage ou de réparation.",
    "insta_DXg2OJTjEhm": "Machine de fabrication ou plotter/laser réalisant un dessin très détaillé sur un support.",
    "insta_DXW47DLjXbc": "Scène dans un salon de coiffure : deux jeunes hommes devant de grands miroirs éclairés, avec un outil de coiffure.",
    "insta_DZNUqipplTx": "Réparation automobile : moteur ouvert avec courroies, poulies et pièces mécaniques visibles.",
    "insta_DZY5hc-vTQW": "Spectacle ou rassemblement inspiré de l'univers Naruto : foule filmant une mise en scène avec fumée et effet lumineux.",
}


def apply(vault: Path) -> int:
    updated = 0
    for reel_id, description in DESCRIPTIONS.items():
        path = vault / "raw" / f"{reel_id}.md"
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        replacement = f"## Description visuelle\n{description}\n\n## Images"
        if "## Description visuelle" in text:
            text = re.sub(
                r"(?ms)^## Description visuelle\s*$\n.*?(?=^## Images)",
                lambda _match: replacement[:-len("## Images")],
                text,
                count=1,
            )
        else:
            text = re.sub(r"## Images", lambda _match: replacement, text, count=1)
        path.write_text(text, encoding="utf-8")
        updated += 1
    print(f"Descriptions visuelles : {updated} fiche(s) mises à jour.")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--vault", required=True)
    args = parser.parse_args()
    apply(Path(args.vault).expanduser().resolve())
