# -*- coding: utf-8 -*-
"""devoir deep learning.ipynb
Automatically generated by Colaboratory.
Original file is located at
    https://colab.research.google.com/drive/11-Makq8wQdi9JAfSdggAvFuRK782-uju
"""

#activation du mode Debug qui permettra d’afficher les erreurs à l’écran.
DEBUG = True

#Classes GenEfficientNet avec des définitions d'architecture basées sur des chaînes de caractères pour configurer les schémas de blocs.
!pip -q install geffnet

# Commented out IPython magic to ensure Python compatibility.
#Import des librairies et modules nécessaires pour le projet
import os
import sys
import time
import numpy as np
import pandas as pd
import cv2
import PIL.Image
import matplotlib.pyplot as plt
# %matplotlib inline
import seaborn as sns
from tqdm.notebook import tqdm # progression 
from sklearn.metrics import roc_auc_score

import torch
from torch.utils.data import TensorDataset, DataLoader, Dataset
import torch.nn as nn
import torch.nn.functional as F
import albumentations as A
import geffnet

device = torch.device('cuda') # GPU utiliser carte graphique configuration

kernel_type = '9c_b7_1e_640_ext_15ep'
image_size = 640 
use_amp = False
data_dir = '../input/jpeg-melanoma-768x768'. # attribut de data_dir à un chemin du dossier
data_dir2 = '../input/jpeg-isic2019-768x768' # attribut de data_dir2 à un chemin
model_dir = '../input/melanoma-best-single-model-no-meta-data'
enet_type = 'efficientnet-b7' #######
batch_size = 32.#nombre d'échantillons qui seront propagés à travers le réseau pour l'entrainement.
num_workers = 4. # num_workers indique à l'instance de chargement des données le nombre de sous-processus à utiliser pour le chargement des données.
out_dim = 9

use_meta = False.  
use_external = '_ext' in kernel_type

"""# READ CSV"""

df_test = pd.read_csv(os.path.join(data_dir, 'test.csv')) # Lecture du fichier test.csv dans data_dir
df_test['filepath'] = df_test['image_name'].apply(lambda x: os.path.join(data_dir, 'test', f'{x}.jpg'))

df_train = pd.read_csv(os.path.join(data_dir, 'train.csv')) # Lecture du fichier train.csv dans data_dir
df_train = df_train[df_train['tfrecord'] != -1].reset_index(drop=True) #retire les index des toutes les colonnes où df_train['tfrecord'] # -1
# df_train['fold'] = df_train['tfrecord'] % 5
# création dictionnaire de valeur pour partitionner les données df
tfrecord2fold = {
    2:0, 4:0, 5:0,
    1:1, 10:1, 13:1,
    0:2, 9:2, 12:2,
    3:3, 8:3, 11:3,
    6:4, 7:4, 14:4,
}   
df_train['fold'] = df_train['tfrecord'].map(tfrecord2fold)  # parcourir tout le dataset et le partitionner selon le dictionnaire tfrecord...
df_train['is_ext'] = 0
df_train['filepath'] = df_train['image_name'].apply(lambda x: os.path.join(data_dir, 'train', f'{x}.jpg')) #   stocke dans filepath les fichier.jpg dans image_name

##############   BKL= benign keratosis ###########
##############   diagnosis - informations détaillées sur le diagnostic (train uniquement) #############
##############   changement de nom de variable dans le fichier d'entrainement dans la colonne diagnosis ###############

df_train['diagnosis'] = df_train['diagnosis'].apply(lambda x: x.replace('seborrheic keratosis', 'BKL')) 
df_train['diagnosis'] = df_train['diagnosis'].apply(lambda x: x.replace('lichenoid keratosis', 'BKL'))
df_train['diagnosis'] = df_train['diagnosis'].apply(lambda x: x.replace('solar lentigo', 'BKL'))
df_train['diagnosis'] = df_train['diagnosis'].apply(lambda x: x.replace('lentigo NOS', 'BKL'))
df_train['diagnosis'] = df_train['diagnosis'].apply(lambda x: x.replace('cafe-au-lait macule', 'unknown')) # tâche de naissance 
df_train['diagnosis'] = df_train['diagnosis'].apply(lambda x: x.replace('atypical melanocytic proliferation', 'unknown'))

df_train['diagnosis'].value_counts() # Obtention du nonmbre de chaque élément dans diagnosis

if use_external:
    df_train2 = pd.read_csv(os.path.join(data_dir2, 'train.csv'))
    df_train2 = df_train2[df_train2['tfrecord'] >= 0].reset_index(drop=True)
    df_train2['fold'] = df_train2['tfrecord'] % 5
    df_train2['is_ext'] = 1
    df_train2['filepath'] = df_train2['image_name'].apply(lambda x: os.path.join(data_dir2, 'train', f'{x}.jpg'))
##############   changement de nom de variable dans le fichier d'entrainement dans la colonne diagnosis ###############
##############   NV par nevus et MEL par melanoma  ###############

    df_train2['diagnosis'] = df_train2['diagnosis'].apply(lambda x: x.replace('NV', 'nevus'))
    df_train2['diagnosis'] = df_train2['diagnosis'].apply(lambda x: x.replace('MEL', 'melanoma'))
    df_train = pd.concat([df_train, df_train2]).reset_index(drop=True)

diagnosis2idx = {d: idx for idx, d in enumerate(sorted(df_train.diagnosis.unique()))}. # Formation d'un dictionnaire  
df_train['target'] = df_train['diagnosis'].map(diagnosis2idx)# Création de la colonne target dans df train en utilisant l'iteration précédente
mel_idx = diagnosis2idx['melanoma'] # Stockage de melanoma qui se trouve dans diagnosis2idx
diagnosis2idx

"""
# Creation de Dataset
"""

class SIIMISICDataset(Dataset): #Class avec dataset en argument
    def __init__(self, csv, split, mode, transform=None): 
##########################################################################
# La méthode particulière __init__qui permet d'initialiser les attributs###
# internes ici, un fichier csv, split mode et transform = None ########@##
# En python, self représente l'instance de la classe ###################@#
# et se place toujours en premier argument d'une méthode.##########@######@
##########################################################################

        self.csv = csv.reset_index(drop=True) # lors de l'import du csv on l'instancie en initialisant ces index par une colonne de valeur de [0;len(dataset))
        self.split = split 
        self.mode = mode
        self.transform = transform

        # Les valeurs de split, mode et transform sont initialisé avec les valeurs choisi lorsque l'on instancie la class SIIMISICDataset

    def __len__(self): #La fonction len est une fonction prédéfinie qui retourne la longueur d'un objet. ici on retourne la taille du fichier CSV
        return self.csv.shape[0]

    def __getitem__(self, index):
        row = self.csv.iloc[index]
        
        image = cv2.imread(row.filepath) # On lit, on charge une image situé dans un chemin specifique à chaque row
        image = image[:, :, ::-1] # On recupere toutes les lignes toutes les colones et la troisieme dimenssion en partant de la derniere valeur jusquà la premiere

        if self.transform is not None: # si transform n'est pas null 
            res = self.transform(image=image) # on transforme ce qu'il y a en image et on converti les données en float
            image = res['image'].astype(np.float32)
        else:
            image = image.astype(np.float32)# sinon on converti les données en float

        image = image.transpose(2, 0, 1) # on transpose notre image la 3eme dimenssion devient lere la premiere devient la deuxiemme et la deuxiemme devient la troisieme

        if self.mode == 'test': 
            return torch.tensor(image).float()# si notre argument mode = test on renvoievun tenseur de données en float de la taille de notre image
        else:
            return torch.tensor(image).float(), torch.tensor(self.csv.iloc[index].target).long() # si notre argument mode = test on renvoievun tenseur de données en float de la taille de notre image et un tenseur de données de la taille de notre target en format long

# Dans le cadre de la data Augmentation en deep learning, ils ont fait appel à la libraire ###### Albumentation avec des fonction tels que transform ou encore compose
# Ici Compose va applique deux transformation à la donnée de notre image un resizing et une normalisation
transforms_val = A.Compose([
    A.Resize(image_size, image_size),
    A.Normalize()
])

df_show = df_train.sample(1000) # on prend un echantillons de 1000 image
dataset_show = SIIMISICDataset(df_show, 'train', 'val', transform=transforms_val) # on applique notre classe, on l'instancie pour obtenir notre dataset
# dataset_show = CloudDataset(df_train, 'train', 'val', image_size, transform=None)
# dataset_show = CloudDataset(df_test, 'test', 'test', image_size, transform=None)
from pylab import rcParams
rcParams['figure.figsize'] = 20,10
for i in range(2):
    f, axarr = plt.subplots(1,5)
    for p in range(5):
        idx = np.random.randint(0, len(dataset_show))
        img, label = dataset_show[idx]
        if use_meta:
            img = img[0]
        axarr[p].imshow(img.transpose(0, 1).transpose(1,2).squeeze())
        axarr[p].set_title(str(label))
# La boucle for nous permet de visualiser nos images plus exactement 2 ranger de 5 images

"""# Model"""

class enetv2(nn.Module):

###############################################################
# le nn .ModuleUn module est un conteneur dont les couches,   #
# les sous-parties de modèle et les modèles doivent hériter,  # 
# l'héritage de nn.Module vous permet d'appeler facilement.   #
# des méthodes comme .eval (), .parameters ().                #
###############################################################
    def __init__(self, backbone, out_dim, n_meta_features=0, load_pretrained=False):

# backbone fait référence au model de base

        super(enetv2, self).__init__()# super () vous donne accès aux méthodes d'une superclasse de la sous-classe qui en hérite.
        self.n_meta_features = n_meta_features # les meta_features sont initialisé à Zero
        self.enet = geffnet.create_model(enet_type.replace('-', '_'), pretrained=load_pretrained)
        #create_model est utilisé pour le deploiement d'un modele,dans les scénarios où vous devez créer un pipeline pour les inférences via plusieurs modèles
        self.dropout = nn.Dropout(0.5)
# Pendant l'entraînement, Dropout() met à zéro au hasard certains des éléments du tenseur d'entrée avec une probabilité 0,5,
# en utilisant des échantillons d'une distribution de Bernoulli
        in_ch = self.enet.classifier.in_features #in_feature est le nombre d'input pour notre couche d'entrée
        self.myfc = nn.Linear(in_ch, out_dim) # transformation linéaire entre le nombre de notre couche d'entrée et de sortie. ça definit nos couches cachées
        self.enet.classifier = nn.Identity() # 
        #enet.classifier permet une sélection de fonctionnalités tout en effectuant une classification, on renvoie l'entrée en tant que telle avec nn.identity().

    def extract(self, x):
        x = self.enet(x)
        return x
###############################################################
# La methode extact permet d'extraire les diffents modèls de Enet instancié dans le module Enet
###############################################################

    def forward(self, x, x_meta=None):
        x = self.extract(x).squeeze(-1).squeeze(-1) # ici on tansforme notre data en vecteur
        x = self.myfc(self.dropout(x)) 
        return x
###############################################################
# 
###############################################################

"""# Validation Function"""

def get_trans(img, I): # En tenant compte des informations que l'on souhaite sur l'image après une opération on génère une image pivoter (retourner ou miroir)
    if I >= 4:
        img = img.transpose(2,3)
    if I % 4 == 0:
        return img
    elif I % 4 == 1:
        return img.flip(2)
    elif I % 4 == 2:
        return img.flip(3)
    elif I % 4 == 3:
        return img.flip(2).flip(3)

    
def val_epoch(model, loader, is_ext=None, n_test=1, get_output=False):
    model.eval()
    LOGITS = []
    PROBS = []
    TARGETS = []
    with torch.no_grad():
        for (data, target) in tqdm(loader): # Faire apparaître un compteur de progression intelligent sur la boucles 
            
            if use_meta: 
                data, meta = data
                data, meta, target = data.to(device), meta.to(device), target.to(device) # Qui déplace un tenseur du CPU ou la mémoire CUDA.

                logits = torch.zeros((data.shape[0], out_dim)).to(device) # Permet d'initialiser les paramètres
                probs = torch.zeros((data.shape[0], out_dim)).to(device) # Qui déplace un tenseur du CPU ou la mémoire CUDA.
                for I in range(n_test):
                    l = model(get_trans(data, I), meta)
                    logits += l
                    probs += l.softmax(1) # Softmax (rendre non linéaire)= Fonction d'activation 
            else:
                data, target = data.to(device), target.to(device)
                logits = torch.zeros((data.shape[0], out_dim)).to(device)
                probs = torch.zeros((data.shape[0], out_dim)).to(device)
                for I in range(n_test):
                    l = model(get_trans(data, I))
                    logits += l
                    probs += l.softmax(1)
            logits /= n_test
            probs /= n_test
# Garder en mémoire le tenseur (persist) . detach
            LOGITS.append(logits.detach().cpu())
            PROBS.append(probs.detach().cpu())
            TARGETS.append(target.detach().cpu())

    LOGITS = torch.cat(LOGITS).numpy(). # Concatène LOGITS le tenseur séquentiels dans la dimension donnée
    PROBS = torch.cat(PROBS).numpy().  #Concatène PROBS le tenseur séquentiels dans la dimension donnée
    TARGETS = torch.cat(TARGETS).numpy() #Concatène TARGETS le tenseur séquentiels dans la dimension donnée

    if get_output:
        return LOGITS, PROBS
    else:
        acc = (PROBS.argmax(1) == TARGETS).mean() * 100.
        auc = roc_auc_score((TARGETS==mel_idx).astype(float), LOGITS[:, mel_idx]) 
        auc_20 = roc_auc_score((TARGETS[is_ext==0]==mel_idx).astype(float), LOGITS[is_ext==0, mel_idx])
        return val_loss, acc, auc, auc_20

PROBS = []
dfs = []

for fold in range(5):
    i_fold = fold
################################# Mask: Filtre les données du dataset dont les valeurs de la colonne fold sont équivalent au valeur de i_fold #########################
    df_valid = df_train[df_train['fold'] == i_fold] 
    if DEBUG:
        df_valid = pd.concat([
            df_valid[df_valid['target'] == mel_idx].sample(10), # Mask avec mel idx 10 echantillons
            df_valid[df_valid['target'] != mel_idx].sample(10)
        ])                                           
    print(df_valid.shape)
################################# Récupère le dataset dit "valide" #############################

    dataset_valid = SIIMISICDataset(df_valid, 'train', 'val', transform=transforms_val)     
    valid_loader = torch.utils.data.DataLoader(dataset_valid, batch_size=batch_size, num_workers=num_workers)

################################## Utilisation du modèle #################################
    model = enetv2(enet_type, n_meta_features=0, out_dim=out_dim) # modèle enetv2
    model = model.to(device)
    model_file = os.path.join(model_dir, f'{kernel_type}_best_o_fold{i_fold}.pth')
    state_dict = torch.load(model_file)
    state_dict = {k.replace('module.', ''): state_dict[k] for k in state_dict.keys()} # énoncé les clés
    model.load_state_dict(state_dict, strict=True)
    model.eval()

    this_LOGITS, this_PROBS = val_epoch(model, valid_loader, is_ext=df_valid['is_ext'].values, n_test=8, get_output=True)
    PROBS.append(this_PROBS)
    dfs.append(df_valid)
################################# Dimension: Supprimer les entrées uni-dimensionnelles #############################
dfs = pd.concat(dfs).reset_index(drop=True)
dfs['pred'] = np.concatenate(PROBS).squeeze()[:, mel_idx]

# Raw auc_all
roc_auc_score(dfs['target'] == mel_idx, dfs['pred'])

# Rank per fold auc_all
dfs2 = dfs.copy() # Duplication de dfs
for i in range(5):
    dfs2.loc[dfs2['fold']==i, 'pred'] = dfs2.loc[dfs2['fold']==i, 'pred'].rank(pct=True) #Classement par percentile
roc_auc_score(dfs2['target'] == mel_idx, dfs2['pred'])   # Score sur ces partitions à lui

# Raw auc_2020
roc_auc_score(dfs[dfs['is_ext']==0]['target']==mel_idx, dfs[dfs['is_ext']==0]['pred'])

# Rank per fold auc_2020
dfs2 = dfs[dfs.is_ext==0].copy()
for i in range(5):
    dfs2.loc[dfs2['fold']==i, 'pred'] = dfs2.loc[dfs2['fold']==i, 'pred'].rank(pct=True)
roc_auc_score(dfs2['target'] == mel_idx, dfs2['pred']).

"""# Predict"""

n_test = 8 
###################### On definit le dataset de test divisant en plusieurs echantillons #########################
df_test = df_test if not DEBUG else df_test.sample(batch_size * 3) 
####################### On definit un autre dataset de Test en utilisant notre classe SIIMISICDataset ######################
dataset_test = SIIMISICDataset(df_test, 'test', 'test', transform=transforms_val)
####################### On charge notre dataset avec la donnée  ######################
test_loader = torch.utils.data.DataLoader(dataset_test, batch_size=batch_size, num_workers=num_workers)

########################################################################################################################################
######################## On initialise notre output par une liste vide que l'on va charger #######################
######################## enetv2 est un modèle permettant d'avoir Une précision donnée ainsi qu'une image size de 600 ###################
#####################################                 https://pypi.org/project/geffnet/             ####################################
########################################################################################################################################
OUTPUTS = [] 
for fold in range(5):
    model = enetv2(enet_type, n_meta_features=0, out_dim=out_dim)
    model = model.to(device) # Qui déplace un tenseur du CPU vers la mémoire CUDA.
    model_file = os.path.join(model_dir, f'{kernel_type}_best_o_fold{i_fold}.pth')
    state_dict = torch.load(model_file)
    state_dict = {k.replace('module.', ''): state_dict[k] for k in state_dict.keys()} # Reconfiguration de tous les objets module.
    model.eval()
###############################################################
#                                                             #
###############################################################
    LOGITS = []
    PROBS = []

    with torch.no_grad(): #. La désactivation du calcul du gradient est utile pour l'inférence, lorsque vous êtes sûr de ne pas appeler Tensor.backward()
        for (data) in tqdm(test_loader): # Progression de la boucle for 
            
            if use_meta:
                data, meta = data
                data, meta = data.to(device), meta.to(device)
                logits = torch.zeros((data.shape[0], out_dim)).to(device) ################ Même principe de réinitialisation que dans Validation Function ####################
                probs = torch.zeros((data.shape[0], out_dim)).to(device)
                for I in range(n_test):
                    l = model(get_trans(data, I), meta)   ##### Utilisation de la fonction get_trans de reconstitution de l'iamge dans Validation Function
                    logits += l
                    probs += l.softmax(1) ######### Fonction d'activation ##############
            else:
                data = data.to(device)
                logits = torch.zeros((data.shape[0], out_dim)).to(device)
                probs = torch.zeros((data.shape[0], out_dim)).to(device)
                for I in range(n_test):
                    l = model(get_trans(data, I))
                    logits += l
                    probs += l.softmax(1)
            logits /= n_test
            probs /= n_test
    
            LOGITS.append(logits.detach().cpu()) ########Stockage des LOGITS ##########
            PROBS.append(probs.detach().cpu())  ########Stockage des PROBS ##########

    LOGITS = torch.cat(LOGITS).numpy() ############# Concatène LOGITS dans la dimension donnée  #################
    PROBS = torch.cat(PROBS).numpy()   ############# Concatène PROBS dans la dimension donnée  #################

    OUTPUTS.append(PROBS[:, mel_idx]) ############# Ajout de toutes les probabilités de mel_idx  #################
