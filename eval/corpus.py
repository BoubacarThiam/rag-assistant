"""Source text of the evaluation PDFs (fictional documents, written for this project).

Fictional on purpose: a model cannot answer from memory, so a correct answer proves that the
retrieval + grounding pipeline worked. Topics deliberately overlap between documents (opening
hours, warranty, Wi-Fi, deadlines) so that retrieval has real distractors.

Run `python -m eval.build_pdfs` after editing this file to regenerate eval/pdfs/.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class CorpusDocument:
    filename: str
    header: str  # repeated at the top of every page (exercises header removal)
    pages: tuple[str, ...]


GUIDE_NOVALIA = CorpusDocument(
    filename="guide-salarie-novalia.pdf",
    header="Novalia SAS - Guide du salarié - Édition 2026",
    pages=(
        # 1
        "Bienvenue chez Novalia. Ce guide rassemble les règles de vie de l'entreprise et les "
        "réponses aux questions les plus fréquentes des nouveaux arrivants. Il ne remplace pas "
        "votre contrat de travail ni la convention collective, mais il en résume les points "
        "pratiques. La durée du travail est de 37 heures par semaine pour un salarié à temps "
        "plein. Les horaires sont variables : chacun organise sa journée librement à condition "
        "d'être présent pendant les plages fixes, de 9 h 30 à 16 h, du lundi au vendredi. "
        "L'arrivée est possible dès 7 h 45 et les locaux ferment à 19 h 30. La pause déjeuner "
        "dure au minimum 45 minutes et n'est pas comptée dans le temps de travail. Le badge "
        "remis le premier jour sert à la fois à ouvrir les portes et à enregistrer les heures "
        "d'arrivée et de départ. En cas de perte, prévenez l'accueil sans attendre : un badge "
        "provisoire vous sera prêté pour cinq jours. Les heures effectuées au-delà de la durée "
        "hebdomadaire alimentent un compteur que vous pouvez consulter sur le portail interne "
        "MonEspace. Ce compteur ne peut pas dépasser 12 heures de crédit en fin de mois. "
        "Les réunions d'équipe ont lieu chaque mardi matin et la présence sur site y est "
        "attendue.",
        # 2
        "Congés et jours de repos. Chaque salarié bénéficie de 27 jours ouvrés de congés payés "
        "par année complète de présence. S'y ajoutent 10 jours de RTT pour les salariés à temps "
        "plein, acquis au fil des mois. Toute demande de congé se fait sur le portail MonEspace "
        "et doit être déposée au moins trois semaines avant la date de départ souhaitée. Votre "
        "responsable dispose de cinq jours ouvrés pour répondre ; sans réponse dans ce délai, "
        "la demande est considérée comme acceptée. Pour les congés d'été, les souhaits sont "
        "recueillis avant le 15 mars afin d'organiser les présences dans chaque service. Les "
        "congés non pris ne sont pas perdus tout de suite : un report de quatre jours au "
        "maximum est autorisé, à condition de les utiliser avant le 30 avril de l'année "
        "suivante. Au-delà, les jours restants sont définitivement perdus, sauf absence longue "
        "pour maladie. Les jours de RTT, eux, ne se reportent jamais d'une année sur l'autre. "
        "En cas d'événement familial, des jours d'absence exceptionnelle sont accordés sur "
        "justificatif : quatre jours pour un mariage ou un pacs, trois jours pour un "
        "déménagement lié à une mutation.",
        # 3
        "Télétravail. Le télétravail est ouvert à tous les postes compatibles, à partir de "
        "quatre mois d'ancienneté dans l'entreprise. Il est limité à deux jours par semaine, "
        "choisis en accord avec le responsable d'équipe. Le mardi ne peut pas être télétravaillé, "
        "car il est réservé aux réunions d'équipe sur site. Pendant une journée de télétravail, "
        "le salarié doit rester joignable par téléphone et par messagerie pendant les plages "
        "fixes. Novalia verse une indemnité forfaitaire de 2,70 euros par jour télétravaillé, "
        "ajoutée automatiquement à la paie du mois suivant. L'entreprise fournit un ordinateur "
        "portable, un casque et, sur demande, un écran supplémentaire. Le fauteuil de bureau "
        "n'est pas fourni. Le télétravail s'effectue au domicile déclaré ; travailler depuis "
        "l'étranger nécessite un accord écrit de la direction des ressources humaines, demandé "
        "au moins un mois à l'avance. En cas de panne de connexion de plus de deux heures, le "
        "salarié doit revenir sur site ou poser une demi-journée de congé. L'accord de "
        "télétravail peut être suspendu par le responsable si l'organisation du service "
        "l'exige, avec un préavis de quinze jours.",
        # 4
        "Frais professionnels. Les dépenses engagées pour une mission sont remboursées sur "
        "présentation des justificatifs originaux. Les repas pris en déplacement sont "
        "remboursés dans la limite de 19 euros par repas. Les nuits d'hôtel sont prises en "
        "charge jusqu'à 110 euros en province et 150 euros à Paris, petit-déjeuner compris. "
        "Le train se réserve en seconde classe pour les trajets de moins de trois heures ; la "
        "première classe est acceptée au-delà. L'usage du véhicule personnel doit être autorisé "
        "avant le départ et donne lieu à des indemnités kilométriques selon le barème fiscal. "
        "Toutes les notes de frais se saisissent dans l'outil Fraisio, accessible depuis le "
        "portail MonEspace. Elles doivent être transmises dans un délai de 45 jours après la "
        "dépense : passé ce délai, le remboursement n'est plus garanti. Le remboursement "
        "intervient par virement, en général sous dix jours après validation par le "
        "responsable. Les amendes et les dépenses personnelles ne sont jamais remboursées. "
        "Une carte de paiement d'entreprise peut être attribuée aux salariés qui se déplacent "
        "plus de six fois par an.",
        # 5
        "Mutuelle et prévoyance. Tous les salariés sont couverts par la mutuelle Alvéa dès "
        "leur premier jour de travail. L'adhésion est obligatoire, sauf cas de dispense prévus "
        "par la loi, par exemple si vous êtes déjà couvert par la mutuelle de votre conjoint. "
        "Novalia prend en charge 65 % de la cotisation ; la part restante, soit 42 euros par "
        "mois pour un salarié seul, est prélevée sur le bulletin de paie. Vous pouvez rattacher "
        "votre conjoint et vos enfants moyennant une cotisation supplémentaire entièrement à "
        "votre charge. La carte de tiers payant est envoyée à votre domicile sous trois "
        "semaines. Le contrat de prévoyance, entièrement financé par l'entreprise, maintient "
        "votre salaire en cas d'arrêt de travail prolongé, après un délai de carence de sept "
        "jours. Tout arrêt maladie doit être signalé à votre responsable le jour même et le "
        "justificatif transmis au service des ressources humaines dans les 48 heures. Une "
        "visite médicale d'information est organisée dans les trois mois qui suivent "
        "l'embauche.",
        # 6
        "Formation et entretiens. Chaque salarié dispose d'un budget de formation de "
        "1 200 euros par an, utilisable pour des formations en lien avec son métier ou son "
        "projet d'évolution. Ce budget ne se cumule pas d'une année sur l'autre. La demande "
        "doit être déposée au moins deux mois avant le début de la formation, accompagnée du "
        "programme et du devis. La référente formation, Mme Claire Fontanel, vous aide à "
        "choisir un organisme et à monter le dossier ; elle reçoit sur rendez-vous le jeudi. "
        "Les formations obligatoires, comme la sécurité incendie, ne sont pas imputées sur "
        "votre budget personnel. L'entretien annuel a lieu chaque année en février avec votre "
        "responsable : il permet de faire le bilan de l'année écoulée et de fixer les "
        "objectifs. Un entretien professionnel, consacré à votre parcours et à vos souhaits "
        "d'évolution, est organisé tous les deux ans. Les comptes rendus sont signés par les "
        "deux parties et conservés dans votre dossier sur MonEspace. Les nouveaux arrivants "
        "suivent un parcours d'intégration de trois jours durant leur premier mois.",
    ),
)

NOTICE_THERMIA = CorpusDocument(
    filename="notice-thermostat-thermia-t200.pdf",
    header="Thermia T200 - Notice d'utilisation",
    pages=(
        # 1
        "Présentation. Le Thermia T200 est un thermostat d'ambiance programmable et connecté, "
        "conçu pour piloter une chaudière ou un plancher chauffant. La boîte contient le "
        "thermostat, son socle mural, deux vis avec chevilles, deux piles AA et la présente "
        "notice. Le thermostat fonctionne sur piles : aucun raccordement au secteur n'est "
        "nécessaire. Dans des conditions normales d'utilisation, l'autonomie des piles est "
        "d'environ 18 mois. L'écran affiche en permanence la température de la pièce, la "
        "température demandée et le mode en cours. Il s'éclaire pendant dix secondes dès qu'un "
        "bouton est pressé. La face avant comporte quatre boutons : les boutons plus et moins "
        "pour régler la température, le bouton Mode pour changer de mode et le bouton OK pour "
        "valider. La plage de réglage va de 5 °C à 30 °C, par pas de 0,5 °C. L'appareil est "
        "prévu pour un usage intérieur uniquement, dans une pièce sèche. Il ne doit pas être "
        "installé dans une salle de bains. Conservez cette notice : elle contient les "
        "informations utiles pour l'installation, la programmation et le dépannage.",
        # 2
        "Installation. Avant toute intervention, coupez l'alimentation électrique de la "
        "chaudière au tableau. Choisissez l'emplacement avec soin, car il détermine la qualité "
        "de la mesure. Le thermostat doit être fixé à 1,50 m du sol, sur un mur intérieur, à "
        "l'abri des courants d'air. Évitez la proximité d'une source de chaleur comme un "
        "radiateur, une lampe ou un téléviseur, ainsi que les endroits exposés au soleil. "
        "Percez deux trous à l'aide du gabarit imprimé au dos de la boîte, placez les "
        "chevilles et vissez le socle. Raccordez ensuite les deux fils venant de la chaudière "
        "aux bornes R et W du socle ; le sens de branchement est indifférent. Insérez les "
        "piles en respectant la polarité, puis clipsez le thermostat sur son socle jusqu'au "
        "déclic. Rétablissez l'alimentation de la chaudière. À la première mise en service, "
        "l'écran vous demande de régler la langue, la date et l'heure. Si vous n'êtes pas à "
        "l'aise avec les raccordements électriques, faites appel à un installateur qualifié. "
        "Une installation non conforme peut annuler la garantie.",
        # 3
        "Programmation. Le T200 propose trois modes de température. Le mode Confort est réglé "
        "en usine sur 20 °C : il est prévu pour les moments où vous êtes présent. Le mode Éco "
        "maintient 16,5 °C et convient à la nuit ou aux absences de quelques heures. Le mode "
        "Hors-gel maintient 7 °C afin de protéger le logement pendant une longue absence. "
        "Chaque température peut être modifiée dans le menu Réglages. Le programme "
        "hebdomadaire permet de définir jusqu'à six plages horaires par jour, chacune associée "
        "au mode Confort ou au mode Éco. Pour créer une plage, appuyez sur Mode pendant trois "
        "secondes, choisissez le jour, puis réglez l'heure de début et l'heure de fin avec les "
        "boutons plus et moins. Vous pouvez copier le programme d'un jour sur un autre. Une "
        "dérogation temporaire est possible à tout moment : modifiez simplement la température "
        "avec les boutons, elle restera active jusqu'à la plage suivante. La fonction "
        "Vacances suspend le programme et applique le mode Hors-gel jusqu'à la date de retour "
        "que vous indiquez.",
        # 4
        "Connexion Wi-Fi. Le T200 se connecte à votre réseau domestique pour être piloté à "
        "distance depuis l'application Thermia Home, disponible sur téléphone et tablette. "
        "Le thermostat est compatible uniquement avec les réseaux Wi-Fi en 2,4 GHz ; les "
        "réseaux en 5 GHz ne sont pas détectés. Pour lancer l'appairage, maintenez le bouton "
        "OK enfoncé pendant cinq secondes : le symbole Wi-Fi clignote à l'écran. Ouvrez "
        "l'application, créez un compte, puis suivez les étapes pour sélectionner votre réseau "
        "et saisir son mot de passe. L'appairage prend environ deux minutes. Si le code E-14 "
        "s'affiche, la connexion au réseau Wi-Fi a échoué : vérifiez le mot de passe et "
        "rapprochez temporairement le thermostat de votre box. Une fois connecté, le "
        "thermostat met son heure à jour automatiquement et reçoit les mises à jour du "
        "logiciel pendant la nuit. Sans connexion, le thermostat continue de fonctionner "
        "normalement avec le programme enregistré. L'application permet aussi de consulter "
        "l'historique des températures sur les trente derniers jours.",
        # 5
        "Dépannage. En cas d'anomalie, un code s'affiche à l'écran. Le code E-07 indique que "
        "la sonde de température est défectueuse : le chauffage est alors coupé par sécurité "
        "et la sonde doit être remplacée. Le code E-21 signale que les piles sont faibles ; "
        "remplacez les deux piles en même temps par des piles alcalines neuves. Si l'écran "
        "reste éteint, vérifiez le sens des piles. Si la chaudière ne démarre pas alors que le "
        "thermostat demande du chauffage, contrôlez le serrage des fils sur les bornes du "
        "socle. Pour réinitialiser le thermostat et retrouver les réglages d'usine, maintenez "
        "simultanément les boutons plus et moins pendant dix secondes, jusqu'à l'affichage du "
        "mot RESET. Attention : cette opération efface le programme hebdomadaire et les "
        "paramètres Wi-Fi. Si la température affichée vous semble inexacte, vous pouvez "
        "appliquer une correction de plus ou moins 3 °C dans le menu Réglages. Si le problème "
        "persiste après ces vérifications, contactez le service après-vente.",
        # 6
        "Garantie et service après-vente. Le Thermia T200 est garanti 3 ans à compter de la "
        "date d'achat, pièces et main-d'oeuvre. La garantie est étendue à 5 ans si vous "
        "enregistrez votre produit dans l'application Thermia Home dans les 60 jours qui "
        "suivent l'achat. Conservez votre facture, elle vous sera demandée pour toute prise "
        "en charge. La garantie ne couvre pas les dommages causés par une chute, une "
        "infiltration d'eau, une installation non conforme ou l'usure normale des piles. "
        "Les pièces détachées sont disponibles pendant dix ans. La sonde de température de "
        "remplacement porte la référence TS-880 ; le socle mural porte la référence SM-210. "
        "Le service après-vente répond du lundi au vendredi, de 9 h à 18 h, par courriel à "
        "l'adresse sav@thermia.example. Avant de le contacter, munissez-vous du numéro de "
        "série inscrit sous le thermostat. En fin de vie, ne jetez pas l'appareil avec les "
        "ordures ménagères : déposez-le dans un point de collecte et recyclez les piles "
        "séparément.",
    ),
)

REGLEMENT_VALMONT = CorpusDocument(
    filename="reglement-mediatheque-valmont.pdf",
    header="Médiathèque de Valmont - Règlement intérieur",
    pages=(
        # 1
        "Inscription. La médiathèque de Valmont est un service public municipal ouvert à tous. "
        "L'entrée et la consultation des documents sur place sont libres et gratuites. Pour "
        "emprunter, une inscription est nécessaire. Elle est gratuite pour les moins de 18 ans, "
        "les étudiants et les demandeurs d'emploi. Pour les adultes habitant la commune, "
        "l'abonnement annuel coûte 12 euros. Pour les personnes qui n'habitent pas la commune, "
        "il coûte 25 euros. L'inscription se fait à l'accueil sur présentation d'une pièce "
        "d'identité et d'un justificatif de domicile de moins de trois mois. Les mineurs "
        "doivent fournir une autorisation signée par un parent ou un responsable légal. La "
        "carte de lecteur est personnelle ; elle est valable un an, de date à date. Son "
        "titulaire est responsable des documents empruntés avec elle. Tout changement "
        "d'adresse doit être signalé. En cas de perte de la carte, son remplacement est "
        "facturé 2 euros. Les collectivités, comme les écoles et les associations, bénéficient "
        "d'une carte spécifique gratuite.",
        # 2
        "Horaires d'ouverture. La médiathèque est ouverte au public le mardi, le jeudi et le "
        "vendredi de 14 h à 18 h 30, le mercredi de 10 h à 18 h 30 et le samedi de 10 h à 17 h. "
        "Elle est fermée le lundi et le dimanche. Pendant les vacances d'été, du 8 juillet au "
        "31 août, les horaires sont réduits : la médiathèque ouvre du mardi au samedi de 9 h "
        "à 13 h. Elle est fermée les jours fériés et pendant la semaine comprise entre Noël "
        "et le jour de l'An. Les fermetures exceptionnelles sont annoncées à l'entrée du "
        "bâtiment et sur le site de la commune. Une boîte de retour, située à gauche de "
        "l'entrée principale, permet de rendre les documents en dehors des heures d'ouverture ; "
        "les jeux vidéo et les documents fragiles ne doivent pas y être déposés. Le dernier "
        "prêt est enregistré dix minutes avant la fermeture. Les groupes scolaires sont "
        "accueillis le jeudi matin, uniquement sur rendez-vous.",
        # 3
        "Prêts. Chaque lecteur peut emprunter jusqu'à 8 documents à la fois, pour une durée de "
        "4 semaines. Parmi ces documents, deux jeux vidéo au maximum peuvent être empruntés en "
        "même temps. Les nouveautés, signalées par une pastille rouge, sont prêtées pour deux "
        "semaines seulement. Le prêt peut être prolongé une fois, pour deux semaines, à "
        "l'accueil ou depuis votre compte en ligne, à condition que le document ne soit pas "
        "réservé par un autre lecteur. Vous pouvez réserver jusqu'à trois documents déjà "
        "empruntés ; vous êtes prévenu par courriel dès qu'ils sont disponibles et vous "
        "disposez alors de dix jours pour venir les chercher. Les dictionnaires, les "
        "encyclopédies et le dernier numéro de chaque revue se consultent uniquement sur "
        "place. Vérifiez l'état des documents avant de les emprunter et signalez toute "
        "anomalie à l'accueil. Il est interdit de réparer soi-même un document abîmé.",
        # 4
        "Retards et pénalités. Tout document doit être rendu au plus tard à la date indiquée "
        "sur le ticket de prêt. En cas de retard, une pénalité de 0,15 euro par jour et par "
        "document est appliquée. Le montant total des pénalités est plafonné à 9 euros par "
        "lecteur. Un premier rappel est envoyé par courriel après sept jours de retard, un "
        "second par courrier après vingt et un jours. Au-delà de 30 jours de retard, le droit "
        "d'emprunter est suspendu jusqu'au retour des documents et au règlement des pénalités. "
        "Un document perdu ou rendu inutilisable doit être remplacé à l'identique ou "
        "remboursé à son prix d'achat. Pour un jeu vidéo ou un film, seul le remboursement "
        "est accepté, en raison des droits de prêt attachés à ces supports. Les pénalités se "
        "règlent à l'accueil, en espèces ou par carte bancaire. En cas de difficulté, vous "
        "pouvez demander un échelonnement auprès de la direction.",
        # 5
        "Espaces numériques. Dix postes informatiques sont à la disposition des lecteurs "
        "inscrits. L'utilisation d'un poste est limitée à une heure par jour et par personne, "
        "afin que chacun puisse y accéder. Les moins de 12 ans doivent être accompagnés d'un "
        "adulte. Les impressions sont payantes : 0,10 euro la page en noir et blanc et "
        "0,40 euro la page en couleur. La numérisation de documents est gratuite. Le Wi-Fi de "
        "la médiathèque est gratuit ; le code d'accès, renouvelé chaque semaine, est remis à "
        "l'accueil sur présentation de la carte de lecteur. Il est interdit d'installer des "
        "logiciels sur les postes et de consulter des sites illégaux ou choquants. Deux "
        "tablettes et une liseuse peuvent être utilisées sur place en échange de la carte de "
        "lecteur. Un atelier d'initiation à l'informatique, gratuit, est proposé le vendredi "
        "à 15 h ; l'inscription se fait à l'accueil, dans la limite de six participants.",
        # 6
        "Animations et salle d'étude. La salle d'étude, située au premier étage, compte "
        "12 places assises. Elle est accessible sans réservation pour le travail individuel. "
        "Les groupes de quatre personnes ou plus doivent la réserver au moins 48 heures à "
        "l'avance auprès de l'accueil. Le silence y est demandé. L'heure du conte accueille "
        "les enfants à partir de quatre ans chaque mercredi à 16 h, sans inscription. Le club "
        "de lecture se réunit le premier jeudi de chaque mois à 18 h. Des expositions, des "
        "rencontres avec des auteurs et des ateliers sont proposés tout au long de l'année ; "
        "le programme est affiché dans le hall et publié chaque trimestre. Les animations "
        "sont gratuites, mais certaines demandent une inscription préalable en raison du "
        "nombre de places. Les enfants de moins de huit ans restent sous la responsabilité de "
        "l'adulte qui les accompagne pendant toute la durée de leur présence. Il est interdit "
        "de manger dans les espaces de lecture ; les boissons fermées sont tolérées.",
    ),
)


def _variant(
    source: CorpusDocument, filename: str, header: str, replacements: dict[str, str]
) -> CorpusDocument:
    """A "twin" document: same structure and topics, other names and other figures.

    Twins are hard distractors: for "How many days off at Novalia?", the Orvane page about days
    off looks almost identical. Retrieval must rank the right company first, and the answer must
    not mix the two up. That is a realistic difficulty (several versions of a policy, several
    products of a range) which a tiny corpus of unrelated documents would not have.
    """
    full_text = " ".join(source.pages)
    missing = [old for old in replacements if old not in full_text]
    if missing:
        raise ValueError(f"{filename}: replacements not found in the source text: {missing}")

    def rewrite(text: str) -> str:
        for old, new in replacements.items():
            text = text.replace(old, new)
        return text

    return CorpusDocument(filename, header, tuple(rewrite(page) for page in source.pages))


GUIDE_ORVANE = _variant(
    GUIDE_NOVALIA,
    "guide-salarie-orvane.pdf",
    "Orvane Industries - Guide du salarié - Édition 2026",
    {
        "Novalia": "Orvane",
        "MonEspace": "Intralien",
        "Fraisio": "Notéo",
        "Alvéa": "Séréna",
        "Mme Claire Fontanel": "Mme Hélène Marchetti",
        "37 heures": "35 heures",
        "de 9 h 30 à 16 h": "de 10 h à 15 h 30",
        "27 jours ouvrés": "25 jours ouvrés",
        "10 jours de RTT": "8 jours de RTT",
        "au moins trois semaines avant": "au moins un mois avant",
        "un report de quatre jours": "un report de six jours",
        "avant le 30 avril": "avant le 31 mai",
        "à partir de quatre mois d'ancienneté": "à partir de six mois d'ancienneté",
        "limité à deux jours par semaine": "limité à trois jours par semaine",
        "2,70 euros": "3,10 euros",
        "19 euros par repas": "22 euros par repas",
        "110 euros en province et 150 euros à Paris": "95 euros en province et 140 euros à Paris",
        "délai de 45 jours": "délai de 60 jours",
        "65 % de la cotisation": "55 % de la cotisation",
        "42 euros par mois": "51 euros par mois",
        "1 200 euros par an": "900 euros par an",
        "chaque année en février": "chaque année en novembre",
    },
)

NOTICE_CLIMEO = _variant(
    NOTICE_THERMIA,
    "notice-thermostat-climeo-c50.pdf",
    "Climéo C50 - Notice d'utilisation",
    {
        "Thermia T200": "Climéo C50",
        "T200": "C50",
        "Thermia Home": "Climéo Connect",
        "sav@thermia.example": "assistance@climeo.example",
        "environ 18 mois": "environ 24 mois",
        "fixé à 1,50 m du sol": "fixé à 1,30 m du sol",
        "réglé en usine sur 20 °C": "réglé en usine sur 19 °C",
        "maintient 16,5 °C": "maintient 17 °C",
        "maintient 7 °C": "maintient 8 °C",
        "jusqu'à six plages horaires": "jusqu'à quatre plages horaires",
        "E-14": "E-11",
        "E-07": "E-03",
        "E-21": "E-25",
        "pendant dix secondes, jusqu'à l'affichage": "pendant huit secondes, jusqu'à l'affichage",
        "garanti 3 ans": "garanti 2 ans",
        "étendue à 5 ans": "étendue à 4 ans",
        "dans les 60 jours": "dans les 30 jours",
        "TS-880": "CS-415",
        "SM-210": "CM-120",
    },
)

REGLEMENT_BREVIGNY = _variant(
    REGLEMENT_VALMONT,
    "reglement-mediatheque-brevigny.pdf",
    "Médiathèque de Brévigny - Règlement intérieur",
    {
        "Valmont": "Brévigny",
        "coûte 12 euros": "coûte 10 euros",
        "coûte 25 euros": "coûte 30 euros",
        "Elle est fermée le lundi et le dimanche": "Elle est fermée le dimanche et le mardi",
        "le mardi, le jeudi et le vendredi": "le lundi, le jeudi et le vendredi",
        "jusqu'à 8 documents à la fois, pour une durée de 4 semaines": (
            "jusqu'à 6 documents à la fois, pour une durée de 3 semaines"
        ),
        "deux jeux vidéo au maximum": "trois jeux vidéo au maximum",
        "0,15 euro par jour": "0,20 euro par jour",
        "plafonné à 9 euros": "plafonné à 12 euros",
        "Au-delà de 30 jours de retard": "Au-delà de 45 jours de retard",
        "Le Wi-Fi de la médiathèque est gratuit": "Le Wi-Fi de la médiathèque est payant",
        "12 places assises": "16 places assises",
    },
)

DOCUMENTS: tuple[CorpusDocument, ...] = (
    GUIDE_NOVALIA,
    GUIDE_ORVANE,
    NOTICE_THERMIA,
    NOTICE_CLIMEO,
    REGLEMENT_VALMONT,
    REGLEMENT_BREVIGNY,
)
