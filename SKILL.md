---
name: documents-seyegarage
description: Règles métier pour produire les documents de SeyeGarage (pro forma, bon de réception, facture, facture acquittée) : marges, lignes, totaux, mise en page. À lire avant de toucher aux calculs ou aux PDF.
---

# Règles métier des documents

Ces règles viennent de l'outil Excel + Python déjà utilisé par GIE SEYE & FRERES et Seye Motor. Le site doit donner exactement les mêmes résultats.

## Les trois documents d'un dossier
| Document | Contenu | Prix |
|---|---|---|
| **Pro forma** | Devis envoyé au client avant travaux | Oui (marge incluse si renseignée) |
| **Bon de réception** | Remis à la livraison, remplace le « bordereau de livraison » | **Non** |
| **Facture** | Facture finale ; titre **« Facture acquittée »** si le reste à payer est 0 | Oui |

Plus : un PDF « dossier complet » qui les réunit.

## Marge
- Champ vide = **aucune marge**. Il n'y a plus de minimum.
- Valeurs acceptées : `5`, `5%`, `0,05` → 5 % ; `1` → 1 %. Au-delà de 30 %, afficher un avertissement.
- Option « marge aussi sur la facture » (par défaut OUI) : la facture reprend les prix avec marge.
- La marge ne s'affiche jamais comme ligne séparée : elle est **intégrée aux prix**. Un récapitulatif des marges est interne et ne se donne pas au client.
- Marge par défaut possible au niveau de l'entreprise.

## Lignes
- Quantité vide, espace ou tiret = main d'œuvre ou forfait : total de ligne = prix.
- Prix vide ou tiret = 0.
- Quantité décimale acceptée, deux décimales au plus (1,5 m ; 0,5 L). Le total de la ligne est arrondi au franc (1,5 × 333 = 500 F).
- Limites par page : 23 lignes (facture, pro forma), 22 (bon de réception).
- Une ligne sans désignation mais avec un montant déclenche une alerte.

## Totaux
- Total = somme des lignes (avec marge si applicable).
- Reste à payer = total − versements. Reste = 0 → facture acquittée.
- Montant en lettres (français) selon l'option de l'entreprise.

## Mise en page
- En-tête : logo en haut à gauche, identité de l'entreprise ; pied : NINEA, RCCM, compte, banque.
- Tableau encadré, titre centré, modèles de référence : Mecatrozone (facture IN2609-1078, bon de réception BL2610-0012).
- Bloc véhicule sous le client : immatriculation, marque et type, **kilométrage** (« 45 000 km ») si renseigné.
- Thèmes : **classique** (par défaut, marine/orange/gris), **eco** (peu d'encre), **charte** (noir/rouge/argent, plus chargé en encre). Le classique est le choix retenu par défaut.
- Conditions et mode de règlement : valeurs du dossier, sinon valeurs par défaut de l'entreprise.

## Identité à ne pas inventer
NINEA et RCCM viennent des paramètres de l'entreprise. Si absents : afficher « en cours d'obtention » seulement si l'entreprise l'a saisi ainsi.
