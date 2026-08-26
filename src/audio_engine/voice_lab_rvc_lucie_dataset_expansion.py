"""Frozen neutral Lucie corpus expansion after the 10-clip machine-qualified pilot.

All 60 texts and seeds are fixed before synthesis. No retries, substitutions or
emotion instructions are permitted. The corpus is Voice Lab evidence only.
"""
from __future__ import annotations

import hashlib

PILOT_RUN_ID = 32939596171
PILOT_ARTIFACT = "rvc-lucie-neutral-dataset-pilot-qualified-parallel"
SELECTED_PAIR_RUN_ID = 32818950167
SELECTED_PAIR_ARTIFACT = "qwen3-contrast-selected-pair"
LUCIE_ANCHOR_SHA256 = "9e5ff59c1b2993b249851bfd3a9f8e78047fd5afd93b034392df1977ae54c822"
CLAIRE_ANCHOR_SHA256 = "3366f993d108f42525627f1be03e71fdec312b559e067616d2019b69da35cafe"
QWEN_REVISION = "022e286b98fbec7e1e916cb940cdf532cd9f488e"
BASE_MODEL_ID = "Qwen/Qwen3-TTS-12Hz-1.7B-Base"
BASE_MODEL_REVISION = "74a6279626edc2d5a787d5b6467668eba0b86ef6"

# Neutral declarative French with deliberately broad phonetic, syntactic and
# lexical coverage. No emotional stage directions or acting cues.
CANDIDATES = (
    ("n11", "Au bout du quai, le panneau indique les horaires des prochains bateaux vers les îles."),
    ("n12", "Chaque mardi, le boulanger dépose deux paniers devant la porte de la petite épicerie."),
    ("n13", "La bibliothèque ferme à dix-huit heures, sauf le jeudi où les lecteurs restent plus tard."),
    ("n14", "Près de la fontaine, cinq bancs entourent un carré de lavande et de jeunes rosiers."),
    ("n15", "J'ai rangé les factures par année afin de retrouver rapidement les montants déjà vérifiés."),
    ("n16", "Le chemin traverse une prairie humide avant de rejoindre la route bordée de peupliers."),
    ("n17", "À huit heures vingt, le premier autobus quitte la gare et dessert quatre villages voisins."),
    ("n18", "Nous avons choisi une table près de la fenêtre pour profiter de la lumière du matin."),
    ("n19", "Le mécanicien contrôlera les pneus, les freins et le niveau d'huile avant notre départ."),
    ("n20", "Dans cette armoire, les chemises blanches sont à gauche et les dossiers verts à droite."),
    ("n21", "La pluie de la nuit a laissé de petites flaques entre les pavés de la cour intérieure."),
    ("n22", "Mon voisin cultive des tomates jaunes, des courgettes et quelques herbes près du mur."),
    ("n23", "Le musée présente une maquette du port tel qu'il apparaissait au début du siècle dernier."),
    ("n24", "Nous comparerons les deux itinéraires avant de réserver les billets pour le mois de juin."),
    ("n25", "Une horloge ronde est fixée au-dessus du guichet, juste en face de l'escalier principal."),
    ("n26", "Le courrier du vendredi comprend trois enveloppes, un catalogue et une carte postale."),
    ("n27", "Cette vieille maison possède un grenier bas, deux cheminées et une cave voûtée en pierre."),
    ("n28", "À la sortie du tunnel, la vallée s'élargit et les collines deviennent moins abruptes."),
    ("n29", "Le professeur a demandé une copie lisible, datée et signée avant la fin de la semaine."),
    ("n30", "Sur l'étagère du haut, les dictionnaires sont classés par langue puis par ordre alphabétique."),
    ("n31", "Les fenêtres du salon donnent sur une cour calme où pousse un grand marronnier."),
    ("n32", "Nous avons mesuré la pièce avant de commander la nouvelle table et les six chaises."),
    ("n33", "Le marché ouvre tôt le samedi et les producteurs arrivent souvent avant le lever du soleil."),
    ("n34", "Une passerelle métallique relie les deux bâtiments au-dessus d'une petite rue pavée."),
    ("n35", "Je laisserai le dossier rouge sur votre bureau avec la liste des documents manquants."),
    ("n36", "Le train régional s'arrête ici pendant deux minutes avant de poursuivre vers le nord."),
    ("n37", "Dans le parc, un sentier circulaire longe l'étang puis revient vers l'entrée principale."),
    ("n38", "La recette prévoit quatre œufs, deux cents grammes de farine et un peu de vanille."),
    ("n39", "Nous passerons d'abord par la poste, puis par la pharmacie située derrière la mairie."),
    ("n40", "Le nouveau règlement sera affiché près de l'accueil dès le premier jour du mois prochain."),
    ("n41", "La route suit la rivière sur plusieurs kilomètres avant de monter doucement vers le plateau."),
    ("n42", "Une plaque de cuivre porte encore le nom de l'ancien propriétaire et la date de construction."),
    ("n43", "Le téléphone sonne rarement dans cette salle, car les appels arrivent surtout à l'accueil."),
    ("n44", "J'ai posé les verres dans le placard du haut et les assiettes sur l'étagère du milieu."),
    ("n45", "Les visiteurs peuvent emprunter un plan gratuit à l'entrée puis le rendre en partant."),
    ("n46", "Le village compte une école, une petite église et plusieurs maisons alignées autour de la place."),
    ("n47", "Nous noterons les mesures dans le tableau avant de calculer la moyenne de chaque série."),
    ("n48", "Le portail en bois reste ouvert pendant la journée et se ferme automatiquement à vingt heures."),
    ("n49", "Cette boîte contient des vis de plusieurs tailles, des rondelles et deux petites clés plates."),
    ("n50", "Au printemps, les oiseaux reviennent dans les haies et les jardins deviennent rapidement plus verts."),
    ("n51", "La salle du fond peut accueillir trente personnes autour de cinq grandes tables rectangulaires."),
    ("n52", "Nous avons reçu la confirmation hier et le colis devrait arriver entre mercredi et vendredi."),
    ("n53", "Un panneau discret indique le passage vers la cour, derrière le grand rideau gris."),
    ("n54", "Le café sert le petit déjeuner jusqu'à onze heures et propose ensuite un menu plus court."),
    ("n55", "La façade a été nettoyée récemment, mais les volets conservent leur ancienne couleur bleue."),
    ("n56", "Je vais vérifier le numéro de la salle avant d'imprimer les invitations pour demain."),
    ("n57", "Le sentier devient plus étroit après le pont et traverse ensuite un petit bois de chênes."),
    ("n58", "Nous avons gardé les anciennes photographies dans une enveloppe épaisse au fond du tiroir."),
    ("n59", "Le compteur affiche exactement cent vingt-sept kilomètres depuis le dernier plein de carburant."),
    ("n60", "Dans la cuisine, une fenêtre étroite éclaire le plan de travail près de l'évier."),
    ("n61", "Les archives municipales conservent plusieurs registres écrits entre dix-huit cent quatre-vingt et dix-neuf cents."),
    ("n62", "Un léger virage à droite conduit vers la place où se trouvent la banque et la librairie."),
    ("n63", "Je déposerai les clés à l'accueil après avoir fermé les fenêtres du deuxième étage."),
    ("n64", "Le calendrier mural montre les vacances scolaires, les jours fériés et les principales échéances."),
    ("n65", "Nous avons acheté du pain complet, des pommes, du fromage et une bouteille d'eau gazeuse."),
    ("n66", "La petite route franchit deux ruisseaux avant d'atteindre les premières maisons du hameau."),
    ("n67", "Le technicien remplacera le câble endommagé puis vérifiera le fonctionnement des trois prises."),
    ("n68", "Sur le bureau, le crayon est posé entre le carnet quadrillé et la lampe articulée."),
    ("n69", "La réunion commencera à quatorze heures précises et devrait se terminer avant seize heures trente."),
    ("n70", "Quand le soleil apparaît derrière les toits, la rue s'éclaire progressivement jusqu'au carrefour."),
)


def seed_for(candidate_id: str) -> int:
    payload = f"rvc-lucie-neutral-expansion-v1\0{candidate_id}".encode("utf-8")
    return int.from_bytes(hashlib.sha256(payload).digest()[:4], "big")


def expansion_spec() -> dict:
    return {
        "schema": "rvc-lucie-neutral-dataset-expansion-v1",
        "role": "lucie",
        "pilot_run_id": PILOT_RUN_ID,
        "pilot_artifact": PILOT_ARTIFACT,
        "selected_pair_run_id": SELECTED_PAIR_RUN_ID,
        "selected_pair_artifact": SELECTED_PAIR_ARTIFACT,
        "lucie_anchor_sha256": LUCIE_ANCHOR_SHA256,
        "claire_anchor_sha256": CLAIRE_ANCHOR_SHA256,
        "qwen_revision": QWEN_REVISION,
        "base_model": {"id": BASE_MODEL_ID, "revision": BASE_MODEL_REVISION},
        "candidates": [
            {"id": cid, "text": text, "seed": seed_for(cid)} for cid, text in CANDIDATES
        ],
        "candidate_count": len(CANDIDATES),
        "render_shards": 6,
        "candidates_per_shard": 10,
        "retries": 0,
        "substitutions": 0,
        "emotion_instruction": False,
        "clip_gates": {
            "technical": "finite speech, non-silent, unclipped, 1.5-10.0 s",
            "identity": "independent WeSpeaker sim(Lucie) > sim(Claire)",
            "french": "Whisper Small WER <= 0.20",
        },
        "final_dataset_gates": {
            "accepted_duration_seconds": ">=300 including exact 10-clip pilot",
            "aggregate_french": "word-count-weighted WER <=0.05 across accepted pilot+expansion",
            "expansion_acceptance_rate": ">=0.85 of the fixed 60 expansion candidates",
            "retry": False,
            "substitution": False,
        },
        "training_authorized_by_generation_workflow": False,
        "human_gate": False,
        "production_qualified": False,
    }
