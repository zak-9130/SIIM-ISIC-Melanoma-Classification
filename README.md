# SIIM-ISIC-Melanoma-Classification
Les codes avec le langage Python.py

--Installation and Requirement

- sklearn.metrics 
- tqdm.notebook
- PIL.Image
- matplotlib.pyplot
- albumentations
- torch.utils.data
Methode special: 
- Geffnet : méthode efficient net : modèles Effnet-B7 avec une taille d'entrée de 640
- Enetv2 : modèle d’un format spécifique
- Librairie albumentation : Pour créer plus de data
- Tqdm :Visualiser la progression de nos itération

Table of Contents
Introduction
Le mélanome est une tumeur maligne développée à partir des mélanocytes (cellule épithéliale qui sécrète de la mélanine qui est à l'origine de la pigmentation de la peau et des poils).
C'est l'un des cancers les plus agressifs qui soient, mais le traitement à une phase qui permet de guérir le patient.

La fréquence du mélanome est en augmentation rapide dans le monde entier.
Le cancer de la peau est le type de cancer le plus répandu. Le mélanome, en particulier, est responsable de 75 % des décès dus au cancer de la peau, bien qu'il s'agisse du cancer de la peau le moins fréquent. L'American Cancer Society estime que plus de 100 000 nouveaux cas de mélanome seront diagnostiqués en 2020. On s'attend également à ce que près de 7 000 personnes meurent de cette maladie. Comme pour les autres cancers, une détection précoce et précise, potentiellement aidée par la science des données, peut rendre le traitement plus efficace.
L'objectif de ce "repo" est de réaliser une explication complète des différentes méthodes utilisés par Qishen Ha
(Machine Learning Engineer chez LINE corp.
Tokyo, Japan) pour obtenir une excellente place au concours Kaggle sur la Classification SIIM-ISIC du mélanome.
Ce "repo" concerne le résultat du concours Kaggle "SIIM-ISIC Melanoma Classification" où il s'agissait d'identifier le mélanome sur les images de lésions cutanées permettant de développer un outil d'analyse d'images cutanées qui pourraient aider les dermatologues cliniciens.
Le modèle ici doit prédire une target binaire pour chaque image. La prédiction est proche de 0 lorsque la lésion est bénigne et proche de 1 lorsqu’elle indique une lésion maligne.

License 
Licence internationale non commerciale 4.0 : https://creativecommons.org/licenses/by-nc/4.0/legalcode.txt 


Implementation Details and Training Process

DATA: L'ensemble de données contient 33126 images d'entrainement dermoscopiques de lésions cutanées bénignes et malignes provenant de plus de 2000 patients. Chaque image es associée à l'une de ces personnes à l'aide d'un identifiant unique du patient.
 L'ensemble de données a été généré par la Collaboration internationale en imagerie cutanée (ISIC) et les images proviennent des sources suivantes : Hôpital Clínic de Barcelone, Université de médecine de Vienne, Centre du cancer Memorial Sloan Kettering, Institut du mélanome d'Australie, Université du Queensland, et l'école de médecine de l'Université d'Athènes.
- train.csv - le kit de formation
- test.csv - le jeu de test
- sample_submission.csv - un exemple de fichier de soumission dans le format correct

Colonnes des fichiers :
- image_name : identifiant unique, renvoie au nom de fichier de l'image DICOM correspondante
- patient_id : identifiant unique du patient
- le sexe :  le sexe du patient 
- age_approx : âge approximatif du patient au moment de l'imagerie
- anatom_site_general_challenge :  localisation du site imagé
- diagnostic : informations détaillées sur le diagnostic (train uniquement)
- benign_malignant :  indicateur de malignité d'une lésion imagée
- target : version binarisée de la cible (maligne)

Différentes Parties du codage

- Read CSV 
- Model : 
- Validation function
- Predict

Conclusion

- Auc_all :
--->    Roc_auc_score = 0.94
--->    Roc_auc_score per fold= 0.94

- Auc_2020 :
--->  Roc_auc=0.8974358974358975
--->  Roc_auc per fold =0.9615384615384615






