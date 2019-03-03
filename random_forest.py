# -*- coding: utf-8 -*-
"""Random forest.ipynb

Automatically generated by Colaboratory.

# Random forest main files
Code editor: Xinyi Li, Yinchuan Li. Date: 2019.2.20.

The code is run on Google Colaboratory with Python 3.

Paper: Mid-LSTM meets Mid-ARMA: deep learning for midterm stock prediction.
"""

!apt-get install -y -qq software-properties-common python-software-properties module-init-tools
!add-apt-repository -y ppa:alessandro-strada/ppa 2>&1 > /dev/null
!apt-get update -qq 2>&1 > /dev/null
!apt-get -y install -qq google-drive-ocamlfuse fuse
from google.colab import auth
auth.authenticate_user()
from oauth2client.client import GoogleCredentials
creds = GoogleCredentials.get_application_default()
import getpass
!google-drive-ocamlfuse -headless -id={creds.client_id} -secret={creds.client_secret} < /dev/null 2>&1 | grep URL
vcode = getpass.getpass()
!echo {vcode} | google-drive-ocamlfuse -headless -id={creds.client_id} -secret={creds.client_secret}

!mkdir -p drive
!google-drive-ocamlfuse drive

import os
os.chdir("drive/download data/sp500new")
# !ls
from google.colab import files
import os
import json
import time
import math
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import datetime as dt
from numpy import newaxis
from keras.layers import Dense, Activation, Dropout, LSTM
from keras.models import Sequential, load_model
from keras.callbacks import EarlyStopping, ModelCheckpoint
from sklearn.linear_model import LinearRegression
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import Ridge

from math import pi,sqrt,exp,pow,log
from numpy.linalg import det, inv
from abc import ABCMeta, abstractmethod
from sklearn import cluster

import statsmodels.api as sm 
import scipy.stats as scs
import scipy.optimize as sco
import scipy.interpolate as sci
from scipy import stats

def stock_RF_loop (filename):

  split = (0.85);
  sequence_length=60;
  normalise= True
  batch_size=60;
  input_dim=4
  input_timesteps=sequence_length-1
  neurons=60
  epochs=2
  prediction_len=60
  dense_output=4
  window_size=sequence_length

  dataframe = pd.read_csv(filename)
  
  #pre stock put on first
  cols = ['Close_y', 'Volume_y','Close_x'];#corr will be add on later


  len_dataframe=dataframe.shape[0]
  corr_num=int(len_dataframe/sequence_length)
  remainder=len_dataframe-corr_num*sequence_length

  # caculate corr table
  corr_win=[]
  corr=np.zeros((len_dataframe))
  for i in range(0,corr_num):
    stock1=[]
    stock2=[]
    for j in range(i*sequence_length,i*sequence_length+sequence_length):
      stock1.append(dataframe[cols[0]][j])
      stock2.append(dataframe[cols[2]][j])
    corr_win.append(np.corrcoef(stock1, stock2)[0,1])
    for j in range(i*sequence_length,i*sequence_length+sequence_length):
      corr[j]=corr_win[i]


  corr_win_remainder=[] 
  stock1_remainder=[]
  stock2_remainder=[] 
  for k in range(0,remainder):
    stock1_remainder.append(dataframe[cols[0]][corr_num*sequence_length+k])
    stock2_remainder.append(dataframe[cols[2]][corr_num*sequence_length+k])
  corr_win_remainder.append(np.corrcoef(stock1_remainder, stock2_remainder)[0,1])
  for q in range(0,remainder):
    corr[corr_num*sequence_length+q]=corr_win_remainder[0]

  i_split = int(len(dataframe) * split)
  data_train = dataframe.get(cols).values[:i_split]
  data_test  = dataframe.get(cols).values[i_split:]
  len_train  = len(data_train)
  len_test   = len(data_test)
  len_train_windows = None

  corr_df=pd.DataFrame(corr)
  data_corr_train=corr_df.values[:i_split]
  data_corr_test=corr_df.values[i_split:]

  #get_test_data   #############################################################

  data_windows = []
  for i in range(len_test - sequence_length):
    data_windows.append(data_test[i:i+sequence_length])
  data_windows = np.array(data_windows).astype(float)

  # get original y_test
  y_test_ori = data_windows[:, -1, [0]]

  window_data=data_windows
  win_num=window_data.shape[0]
  row_num=window_data.shape[1]
  col_num=window_data.shape[2]
  normalised_data = []
  record_min=[]
  record_max=[]

  for win_i in range(0,win_num):
    normalised_window = []
    for col_i in range(0,col_num):
      temp_col=window_data[win_i,:,col_i]
      temp_min=min(temp_col)
      if col_i==0:
        record_min.append(temp_min)#record min
      temp_col=temp_col-temp_min
      temp_max=max(temp_col)
      if col_i==0:
        record_max.append(temp_max)#record max
      temp_col=temp_col/temp_max
      normalised_window.append(temp_col)
    normalised_window = np.array(normalised_window).T
    normalised_data.append(normalised_window)
  normalised_data=np.array(normalised_data)

  corr_windows = []
  for i in range(len_test - sequence_length):
    corr_windows.append(data_corr_test[i:i+sequence_length])
  corr_windows = np.array(corr_windows).astype(float)

  get_test_data=[]
  for win_i in range(0,win_num):
    df1=pd.DataFrame(normalised_data[win_i,:,:])
    df1['corr']=corr_windows[win_i,:,:]
    df2=df1.values
    get_test_data.append(df2)
  get_test_data=np.array(get_test_data)  

  data_windows=get_test_data
  x_test = data_windows[:, :-1]
  y_test = data_windows[:, -1, [0]]

  #get_train_data ##############################################################
  data_windows = []
  for i in range(len_train - sequence_length):
    data_windows.append(data_train[i:i+sequence_length])
  data_windows = np.array(data_windows).astype(float)

  window_data=data_windows
  win_num=window_data.shape[0]
  row_num=window_data.shape[1]
  col_num=window_data.shape[2]

  normalised_data = []
  for win_i in range(0,win_num):
    normalised_window = []
    for col_i in range(0,col_num):
      temp_col=window_data[win_i,:,col_i]
      temp_min=min(temp_col)
      temp_col=temp_col-temp_min
      temp_max=max(temp_col)
      temp_col=temp_col/temp_max
      normalised_window.append(temp_col)
    normalised_window = np.array(normalised_window).T
    normalised_data.append(normalised_window)
  normalised_data=np.array(normalised_data)

  corr_windows_train = []
  for i in range(len_train - sequence_length):
    corr_windows_train.append(data_corr_train[i:i+sequence_length])
  corr_windows_train = np.array(corr_windows_train).astype(float)

  get_train_data=[]
  for win_i in range(0,win_num):
    df1=pd.DataFrame(normalised_data[win_i,:,:])
    df1['corr']=corr_windows_train[win_i,:,:]
    df2=df1.values
    get_train_data.append(df2)
  get_train_data=np.array(get_train_data)  

  data_windows=get_train_data
  x_train = data_windows[:, :-1]
  y_train = data_windows[:, -1]

  ## Random forest
  x_train_rf=pd.DataFrame(x_train[:,:,0])
  y_train_rf=pd.DataFrame(y_train[:,0])
  x_test_rf=pd.DataFrame(x_test[:,:,0])
  y_test_rf=pd.DataFrame(y_test[:,0])
  y_test_ori_rf=pd.DataFrame(y_test_ori[:,0])

  forest = RandomForestRegressor(200)
  forest.fit(x_train_rf, y_train_rf)

  data=x_test[:,:,0]
  prediction_seqs = []
  pre_win_num=int(len(data)/prediction_len)
  window_size=sequence_length

  for i in range(0,pre_win_num):
    curr_frame = data[i*prediction_len]
    predicted = []
    for j in range(0,prediction_len):
      predicted.append(forest.predict(curr_frame[newaxis,:])[0])
      curr_frame = curr_frame[1:]
      curr_frame = np.insert(curr_frame, [window_size-2], predicted[-1], axis=0)
    prediction_seqs.append(predicted)

  #de_predicted
  de_predicted=[]
  len_pre_win=int(len(data)/prediction_len)
  len_pre=prediction_len

  m=0
  for i in range(0,len_pre_win):
    for j in range(0,len_pre):
      de_predicted.append(prediction_seqs[i][j]*record_max[m]+record_min[m])
      m=m+1

  error = []
  diff=y_test.shape[0]-prediction_len*pre_win_num

  for i in range(y_test_ori.shape[0]-diff):
      error.append(y_test_ori[i,] - de_predicted[i])

  squaredError = []
  absError = []
  for val in error:
      squaredError.append(val * val) 
      absError.append(abs(val))

  error_percent=[]
  for i in range(len(error)):
    val=absError[i]/y_test_ori[i,]
    val=abs(val)
    error_percent.append(val)

  mean_error_percent=sum(error_percent) / len(error_percent)
  accuracy=1-mean_error_percent
  
  MSE=sum(squaredError) / len(squaredError)
  return MSE,accuracy,y_test_ori,de_predicted

filename=np.load('filename_delete_sort.npy')
result_RF_df=pd.DataFrame(columns=('index','stock','MSE','accuracy','true','predict'))
n=len(filename)
                           
for i in range(0,100):
  index=i
  stock=filename[i]
  result=stock_RF_loop(filename)
  MSE=result[0]
  accuracy=result[1]
  true=result[2]
  predict=result[3]
  result_RF_df=result_RF_df.append(pd.DataFrame({'index':[index],
                                                     'stock':[stock],
                                                     'MSE':[MSE],
                                                     'accuracy':[accuracy],
                                                     'true':[true],
                                                     'predict':[predict]}),ignore_index=True)
  print(i)
  np.save('RF_451.npy',result_RF_df)
  result_RF_df.to_csv('RF_d0.csv')

#Reshape data
L4_all=np.load('RF_451.npy')
L4_all=pd.DataFrame(L4_all)
L4_all.columns=['MSE','accuracy','index','predict','stock','TRUE']

#accuracy only
filename=np.load('filename_delete_sort.npy')
n=len(filename)
len_pre=360

result_df=pd.DataFrame(columns=('index','stock','TRUE','predict','accuracy','MSE'))
for i in range(0,n):
  index=i
  stock=filename[i]
  #TRUE
  t=[]
  for j in range(0,len_pre):
    t.append(L4_all['TRUE'][i][j][0])
  TRUE=t
  #predict
  t=[]
  for j in range(0,len_pre):
    t.append(L4_all['predict'][i][j])
  predict=t
  #accuracy
  accuracy=[]
  for j in range(0,len_pre):
    t=abs(TRUE[j]-predict[j])/TRUE[j]
    t1=1-t
    accuracy.append(t1)
  accuracy=accuracy
  #MSE
  MSE=L4_all['MSE'][i][0]
  result_df=result_df.append(pd.DataFrame({'index':index,'stock':[stock],
                                           'TRUE':[TRUE],
                                           'predict':[predict],
                                          'accuracy':[accuracy],
                                          'MSE':[MSE]}),
                             ignore_index=True)
  print(i)
np.save('RF_r.npy',result_df)

##Mean MPA of all stocks
RF_r=np.load('RF_r.npy')
RF_r=pd.DataFrame(RF_r)
RF_r.columns=['MSE','TRUE','accuracy','index','predict','stock']

n=451
avg_accuracy1=[]
for i in range(0,360):
  t1=0
  for j in range(0,n):
    t1=t1+RF_r['accuracy'][j][i]
  t1=t1/n
  avg_accuracy1.append(t1)

half1=[]
for i in range(0,6): 
  half1.extend(avg_accuracy1[60*(i+1)-30:60*(i+1)]) 
mean1=pd.DataFrame(half1).mean()[0]

print('Random forest Mean MPA:',mean1)

"""## Portfolio allocation

###Mean variance portfolio allocation based on random forest  (0-60 days) , asset 1.
"""

LH_dph=np.load('RF_r.npy')
LH_dph=pd.DataFrame(LH_dph)
LH_dph.columns = ['MSE','TRUE','accuracy','index','predict','stock']

test_win=6
pre_len1=60
pre_len2=60
stock_len=451
rf=0.015#risk free rate

df_all=pd.DataFrame(columns=('index','return_pre','variance_pre','sharp_pre',
                            'return_true','variance_true','sharp_true',))

filename=np.load('filename_delete_sort.npy')
df = pd.DataFrame()

####cumulative
for k in range(0,test_win):
  n=stock_len
  
  for i in range(0,n):
    t=LH_dph['predict'][i][k*pre_len1:k*pre_len1+pre_len1]
    t1=[]
    for j in range(0,pre_len1):
      t1.append(t[j])
    t=t1
    df[filename[i]]=t  
  data1=df
  log_returns = np.log(data1 / data1.shift(1))
  ret_index = (1 + log_returns).cumprod()
  
  choose_name=[]
  choose_index=[]
  for i in range(0,n):
    if ret_index[filename[i]][59]>1.15:
      choose_name.append(filename[i])
      choose_index.append(i)
      
  #choose data
  m=len(choose_index)
  data2=data1.iloc[:,choose_index]
  log_returns = np.log(data2 / data2.shift(1))
  
  rets = log_returns
  year_ret = rets.mean() * 252
  year_volatility = rets.cov() * 252
  number_of_assets = m
  weights = np.random.random(number_of_assets)
  weights /= np.sum(weights)
  
  def statistics(weights):        
    weights = np.array(weights)
    pret = np.sum(rets.mean() * weights) * 252
    pvol = np.sqrt(np.dot(weights.T, np.dot(rets.cov() * 252, weights)))
    return np.array([pret, pvol, (pret-rf) / pvol])
  
  def min_func_sharpe(weights):
    return -statistics(weights)[2]
    
  bnds = tuple((0,1) for x in range(number_of_assets))
  cons = ({'type': 'eq', 'fun': lambda x: np.sum(x) - 1})

  opts = sco.minimize(min_func_sharpe, 
                      number_of_assets * [1. / number_of_assets,],
                      method='SLSQP', 
                      bounds=bnds, 
                      constraints=cons)
  
  weights_pre=opts['x']
  
  ##check return
  df2 = pd.DataFrame()
  for i in choose_index:
    t=LH_dph['TRUE'][i][k*pre_len1:k*pre_len1+pre_len1]
    t1=[]
    for j in range(0,pre_len1):
      t1.append(t[j])
    t= t1
    df2['ture'+filename[i]]=t
  data3=df2 
  log_returns_true = np.log(data3 / data3.shift(1))
  
  rets_true = log_returns_true
  year_ret_true = rets_true.mean() * 252
  year_volatility_true = rets_true.cov() * 252
  number_of_assets = m  #real asset number
  
  def statistics_true(weights):        
    weights = np.array(weights)
    pret = np.sum(rets_true.mean() * weights) * 252
    pvol = np.sqrt(np.dot(weights.T, np.dot(rets_true.cov() * 252, weights)))
    return np.array([pret, pvol, (pret-rf) / pvol])
  
  index=k
  return_pre=statistics(opts['x'])[0]
  variance_pre=statistics(opts['x'])[1]
  sharp_pre=statistics(opts['x'])[2]
  return_true=statistics_true(opts['x'])[0]
  variance_true=statistics_true(opts['x'])[1]
  sharp_true=statistics_true(opts['x'])[2]
  
  df_all=df_all.append(pd.DataFrame({'index':[index],
                                     'return_pre':[return_pre],
                                     'variance_pre':[variance_pre],
                                     'sharp_pre':[sharp_pre],
                                     'return_true':[ return_true],
                                     'variance_true':[variance_true],
                                    'sharp_true':[sharp_true],}),ignore_index=True)
#   print('stock number:',n)
#   print('count',k)
#   print('choose number',m)
#   print('initial random weight',weights)
#   print('pre weights',opts['x'])
print('Mean variance portfolio allocation based on random forest (0-60 days) , all stocks: \n',df_all)
#   print('weight',opts['x'].round(3))

"""###Minimum variance portfolio allocation based on random forest (0-60 days) , asset 1."""

LH_dph=np.load('RF_r.npy')
LH_dph=pd.DataFrame(LH_dph)
LH_dph.columns = ['MSE','TRUE','accuracy','index','predict','stock']

test_win=6
pre_len1=60
pre_len2=60
stock_len=451
rf=0.015#risk free rate

df_all=pd.DataFrame(columns=('index','return_pre','variance_pre','sharp_pre',
                            'return_true','variance_true','sharp_true',))

filename=np.load('filename_delete_sort.npy')
df = pd.DataFrame()

####cumulative
for k in range(0,test_win):
  n=stock_len
  
  for i in range(0,n):
    t=LH_dph['predict'][i][k*pre_len1:k*pre_len1+pre_len1]
    t1=[]
    for j in range(0,pre_len1):
      t1.append(t[j])
    t=t1
    df[filename[i]]=t  
  data1=df
  log_returns = np.log(data1 / data1.shift(1))
  ret_index = (1 + log_returns).cumprod()
  
  choose_name=[]
  choose_index=[]
  for i in range(0,n):
    if ret_index[filename[i]][59]>1.15:
      choose_name.append(filename[i])
      choose_index.append(i)
      
  #choose data
  m=len(choose_index)
  data2=data1.iloc[:,choose_index]
  log_returns = np.log(data2 / data2.shift(1))
  
  rets = log_returns
  year_ret = rets.mean() * 252
  year_volatility = rets.cov() * 252
  number_of_assets = m
  weights = np.random.random(number_of_assets)
  weights /= np.sum(weights)
  
  def statistics(weights):        
    weights = np.array(weights)
    pret = np.sum(rets.mean() * weights) * 252
    pvol = np.sqrt(np.dot(weights.T, np.dot(rets.cov() * 252, weights)))
    return np.array([pret, pvol, (pret-rf) / pvol])
  
  def min_func_sharpe(weights):
    return statistics(weights)[1]
    
  bnds = tuple((0,1) for x in range(number_of_assets))
  cons = ({'type': 'eq', 'fun': lambda x: np.sum(x) - 1})

  opts = sco.minimize(min_func_sharpe, 
                      number_of_assets * [1. / number_of_assets,],
                      method='SLSQP', 
                      bounds=bnds, 
                      constraints=cons)
  
  weights_pre=opts['x']
  
  ##check return
  df2 = pd.DataFrame()
  for i in choose_index:
    t=LH_dph['TRUE'][i][k*pre_len1:k*pre_len1+pre_len1]
    t1=[]
    for j in range(0,pre_len1):
      t1.append(t[j])
    t= t1
    df2['ture'+filename[i]]=t
  data3=df2 
  log_returns_true = np.log(data3 / data3.shift(1))
  
  rets_true = log_returns_true
  year_ret_true = rets_true.mean() * 252
  year_volatility_true = rets_true.cov() * 252
  number_of_assets = m  #real asset number
  
  def statistics_true(weights):        
    weights = np.array(weights)
    pret = np.sum(rets_true.mean() * weights) * 252
    pvol = np.sqrt(np.dot(weights.T, np.dot(rets_true.cov() * 252, weights)))
    return np.array([pret, pvol, (pret-rf) / pvol])
  
  index=k
  return_pre=statistics(opts['x'])[0]
  variance_pre=statistics(opts['x'])[1]
  sharp_pre=statistics(opts['x'])[2]
  return_true=statistics_true(opts['x'])[0]
  variance_true=statistics_true(opts['x'])[1]
  sharp_true=statistics_true(opts['x'])[2]
  
  df_all=df_all.append(pd.DataFrame({'index':[index],
                                     'return_pre':[return_pre],
                                     'variance_pre':[variance_pre],
                                     'sharp_pre':[sharp_pre],
                                     'return_true':[ return_true],
                                     'variance_true':[variance_true],
                                    'sharp_true':[sharp_true],}),ignore_index=True)
#   print('stock number:',n)
#   print('count',k)
#   print('choose number',m)
#   print('initial random weight',weights)
#   print('pre weights',opts['x'])
print('Minimum variance portfolio allocation based on random forest (0-60 days) , all stocks: \n',df_all)
#   print('weight',opts['x'].round(3))

"""###Mean variance portfolio allocation based on random forest (0-60 days) , asset 2."""

filename=np.load('filename_delete_sort.npy')
sort=np.load('new_sortname.npy')

LH_dph=np.load('RF_r.npy')
LH_dph=pd.DataFrame(LH_dph)
LH_dph.columns = ['MSE','TRUE','accuracy','index','predict','stock']
LH_dph_ori=LH_dph

top=50

LH_dph=[]
for i in range(0,451):
  for j in range(0,top):
    if LH_dph_ori['stock'][i]==sort[j]:
      LH_dph.append(LH_dph_ori.iloc[i,])
      
LH_dph=np.array(LH_dph)
LH_dph=pd.DataFrame(LH_dph)
LH_dph.columns = ['MSE','TRUE','accuracy','index','predict','stock']

test_win=6
pre_len1=60
pre_len2=60
rf=0.015
stock_len=top

df_all=pd.DataFrame(columns=('index','return_pre','variance_pre','sharp_pre',
                            'return_true','variance_true','sharp_true',))

filename=np.load('filename_delete_sort.npy')
df = pd.DataFrame()

rets_true_all=pd.DataFrame()
####cumulative
for k in range(0,test_win):
  n=stock_len
  
  for i in range(0,n):
    t=LH_dph['predict'][i][k*pre_len1:k*pre_len1+pre_len1]
    t1=[]
    for j in range(0,pre_len1):
      t1.append(t[j])
    t=t1
    df[filename[i]]=t  
  data1=df
  log_returns = np.log(data1 / data1.shift(1))
  ret_index = (1 + log_returns).cumprod()
  
  choose_name=[]
  choose_index=[]
  for i in range(0,n):
    if ret_index[filename[i]][59]>1.03:
        choose_name.append(filename[i])
        choose_index.append(i)

  #choose data
  m=len(choose_index)
  data2=data1.iloc[:,choose_index]
  log_returns = np.log(data2 / data2.shift(1))
  
  rets = log_returns
  number_of_assets = m
  weights = np.random.random(number_of_assets)
  weights /= np.sum(weights)
  
  def statistics(weights):        
    weights = np.array(weights)
    pret = np.sum(rets.mean() * weights) * 252
    pvol = np.sqrt(np.dot(weights.T, np.dot(rets.cov() * 252, weights)))
    return np.array([pret, pvol, (pret-rf) / pvol])
  
  def min_func_sharpe(weights):
    return -statistics(weights)[2]
  
  bnds = tuple((0,1) for x in range(number_of_assets))
  cons = ({'type': 'eq', 'fun': lambda x: np.sum(x) - 1})

  opts = sco.minimize(min_func_sharpe, 
                      number_of_assets * [1. / number_of_assets,],
                      method='SLSQP', 
                      bounds=bnds, 
                      constraints=cons)
  
  weights_pre=opts['x']
  
  ##check return
  df2 = pd.DataFrame()
  for i in choose_index:
    t=LH_dph['TRUE'][i][k*pre_len1:k*pre_len1+pre_len1]
    t1=[]
    for j in range(0,pre_len1):
      t1.append(t[j])
    t= t1
    df2['ture'+filename[i]]=t
  data3=df2 
  log_returns_true = np.log(data3 / data3.shift(1))
  
  rets_true = log_returns_true
  a=rets_true_all.append(rets_true,ignore_index=True) 
  number_of_assets = m  #real asset number
  
  def statistics_true(weights):        
    weights = np.array(weights)
    pret = np.sum(rets_true.mean() * weights) * 252
    pvol = np.sqrt(np.dot(weights.T, np.dot(rets_true.cov() * 252, weights)))
    return np.array([pret, pvol, (pret-rf) / pvol])
  
  index=k
  return_pre=statistics(opts['x'])[0]
  variance_pre=statistics(opts['x'])[1]
  sharp_pre=statistics(opts['x'])[2]
  return_true=statistics_true(opts['x'])[0]
  variance_true=statistics_true(opts['x'])[1]
  sharp_true=statistics_true(opts['x'])[2]
  
  df_all=df_all.append(pd.DataFrame({'index':[index],
                                     'return_pre':[return_pre],
                                     'variance_pre':[variance_pre],
                                     'sharp_pre':[sharp_pre],
                                     'return_true':[ return_true],
                                     'variance_true':[variance_true],
                                    'sharp_true':[sharp_true],}),ignore_index=True)
#   print('stock number:',n)
#   print('count',k)
#   print('choose number',m)
#   print('initial random weight',weights)
#   print('pre weights',opts['x'])
#   print('weight',opts['x'].round(3))
print('Mean variance portfolio allocation based on random forest (0-60 days) , asset 2: \n',df_all)