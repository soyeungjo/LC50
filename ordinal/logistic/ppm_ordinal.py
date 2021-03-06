#%%
import sys
sys.path.append('../')

from util import (
      Smiles2Fing,
      mgl_load,
      ppm_load, 
      data_split,
      ParameterGrid,
      MultiCV, 
      OrdinalLogitClassifier
)

import time
import random
import warnings

import pandas as pd
import numpy as np

import matplotlib.pyplot as plt

from sklearn.linear_model import LogisticRegression

import scipy.stats as stats
from sklearn.metrics import classification_report
from sklearn.metrics import (
    precision_score, 
    recall_score, 
    f1_score, 
    accuracy_score, 
    roc_auc_score
    )

# warnings.filterwarnings("ignore")

try:
      import wandb
except: 
      import sys
      import subprocess
      subprocess.check_call([sys.executable, "-m", "pip", "install", "wandb"])
      import wandb


wandb.login(key="1c2f31977d15e796871c32701e62c5ec1167070e")
wandb.init(project="LC50-ppm-ordinal", entity="soyoung")

    

def ppm_ordinal_main(seed_):
    
    path = '../../data/'
    
    ppm, ppm_fingerprints, ppm_y = ppm_load(path)
    train_ppm_fingerprints, train_ppm_y, test_ppm_fingerprints, test_ppm_y = data_split(
        ppm_fingerprints, 
        ppm_y.category,
        seed = seed_
    )


    # print('ppm', 
    #     '\n기초통계량:\n', ppm.value.describe(),
    #     '\n분위수: ', np.quantile(ppm.value, [0.2, 0.4, 0.6, 0.8, 1]))

    # print('범주에 포함된 데이터의 수\n', ppm_y.category.value_counts().sort_index(),
    #     '\n비율\n', ppm_y.category.value_counts(normalize = True).sort_index())

    # print('train 범주에 포함된 데이터의 수\n', train_ppm_y.value_counts().sort_index(),
    #     '\n비율\n', train_ppm_y.value_counts(normalize = True).sort_index())

    # print('test 범주에 포함된 데이터의 수\n', test_ppm_y.value_counts().sort_index(),
    #     '\n비율\n', test_ppm_y.value_counts(normalize = True).sort_index())
    
    '''
        Ordinal Regression with ppm data
    '''
    
    params_dict = {
        'random_state': [seed_], 
        'penalty': ['l1', 'l2'],
        'C': np.linspace(1e-6, 50, 150),
        'solver': ['liblinear', 'saga']
    }

    params = ParameterGrid(params_dict)

    ppm_ordinal_result = MultiCV(
        train_ppm_fingerprints, 
        train_ppm_y, 
        OrdinalLogitClassifier,
        params
    )

    max_tau_idx = ppm_ordinal_result.val_tau.argmax(axis = 0)
    best_params = ppm_ordinal_result.iloc[max_tau_idx][:4].to_dict()

    ordinal = OrdinalLogitClassifier(**best_params)
    ordinal.fit(train_ppm_fingerprints, train_ppm_y)
    ppm_ordinal_pred = ordinal.predict(test_ppm_fingerprints)
      
    result_ = {
        'seed': seed_,
        'parameters': best_params,
        'precision': precision_score(test_ppm_y, ppm_ordinal_pred, average = 'macro'), 
        'recall': recall_score(test_ppm_y, ppm_ordinal_pred, average = 'macro'), 
        'f1': f1_score(test_ppm_y, ppm_ordinal_pred, average = 'macro'), 
        'accuracy': accuracy_score(test_ppm_y, ppm_ordinal_pred),
        'tau': stats.kendalltau(test_ppm_y, ppm_ordinal_pred).correlation
      }
            

    wandb.log({
        'seed': seed_,
        'parameters': best_params,
        'precision': precision_score(test_ppm_y, ppm_ordinal_pred, average = 'macro'), 
        'recall': recall_score(test_ppm_y, ppm_ordinal_pred, average = 'macro'), 
        'f1': f1_score(test_ppm_y, ppm_ordinal_pred, average = 'macro'), 
        'accuracy': accuracy_score(test_ppm_y, ppm_ordinal_pred),
        'tau': stats.kendalltau(test_ppm_y, ppm_ordinal_pred).correlation
    })
      
      
    return result_


result = []
for seed_ in range(200):
      result.append(ppm_ordinal_main(seed_))
      
pd.DataFrame(result).to_csv('../test_results/ppm_ordinal.csv', header = True, index = False)
wandb.finish()
