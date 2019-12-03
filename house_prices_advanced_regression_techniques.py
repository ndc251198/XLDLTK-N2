# -*- coding: utf-8 -*-
"""house-prices-advanced-regression-techniques.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1HAlgAXZn76Lf2zkzb9DUxuwq1XYpdgGI
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime
from scipy.stats import skew
from scipy.special import boxcox1p
from scipy.stats import boxcox_normmax
from sklearn.linear_model import LassoCV, ElasticNetCV, RidgeCV
from sklearn.svm import SVR
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.preprocessing import RobustScaler
from sklearn.model_selection import KFold, cross_val_score
from sklearn.metrics import mean_squared_error
from mlxtend.regressor import StackingCVRegressor
from xgboost import XGBRegressor
from lightgbm import LGBMRegressor
import matplotlib.pyplot as plt
import scipy.stats as stats
import sklearn.linear_model as linear_model
import seaborn as sns
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import make_pipeline
import warnings
warnings.filterwarnings('ignore')

train = pd.read_csv('/house-prices-advanced-regression-techniques/train.csv')
test = pd.read_csv('/house-prices-advanced-regression-techniques/test.csv')
train.head(10)

train[(train['GrLivArea']>4000) & (train['SalePrice']<300000)].index

# loại bỏ dữ liệu nhiễu gây ra bởi thuộc tính GrlivArea
train = train.drop(train[(train['GrLivArea']>4000) & (train['SalePrice']<300000)].index)

train.drop("Id", axis = 1, inplace = True)
test.drop("Id", axis = 1, inplace = True)

# chuyển đổi giá sang phân bố chuẩn
train["SalePrice"] = np.log1p(train["SalePrice"])

ntrain = train.shape[0]
ntest = test.shape[0]
Y_train = train.SalePrice.reset_index(drop=True)
# gộp dữ liệu test và train để xử lý chung
all_data = pd.concat((train, test)).reset_index(drop=True)
all_data.drop(['SalePrice'], axis=1, inplace=True)

ntrain

# một số thuộc tính non-numeric được lưu dạng số, chuyển đổi nó thành string
all_data['MSSubClass'] = all_data['MSSubClass'].apply(str)
all_data['YrSold'] = all_data['YrSold'].astype(str)
all_data['MoSold'] = all_data['MoSold'].astype(str)

all_data_na = (all_data.isnull().sum() / len(all_data)) * 100
all_data_na = all_data_na.drop(all_data_na[all_data_na == 0].index).sort_values(ascending=False)
missing_data = pd.DataFrame({'Missing Ratio' :all_data_na})
missing_data

# loại bỏ các trường không cần thiết
all_data.drop(['PoolQC', 'Utilities'], axis=1, inplace=True)

# các căn nhà có tâng hầm nhưng chưa có chất lượng chiều cao tầng hầm
all_data[(all_data['TotalBsmtSF'] > 0) & (all_data['BsmtQual'].isnull())][['BsmtCond','TotalBsmtSF', 'BsmtQual', 'BsmtExposure', 'BsmtFinType1', 'BsmtFinType2']]

# bổ sung giá trị dựa theo chất lượng chiều cao chiếm nhiều nhất
# modeBsmtQual = all_data['BsmtQual'].mode()[0]
# all_data.loc[2215, 'BsmtQual'] = modeBsmtQual
# all_data.loc[2216, 'BsmtQual'] = modeBsmtQual

# các căn nhà có tâng hầm nhưng chưa có BsmtCond 
all_data[(all_data['TotalBsmtSF'] > 0) & (all_data['BsmtCond'].isnull())][['BsmtCond','TotalBsmtSF', 'BsmtQual', 'BsmtExposure', 'BsmtFinType1', 'BsmtFinType2']]

# Bổ sung giá trị BsmtCond dựa theo các giá trị Bsmt còn lại
all_data.loc[2038, 'BsmtCond'] = 'TA'
all_data.loc[2183, 'BsmtCond'] = 'Fa'
all_data.loc[2522, 'BsmtCond'] = 'Po'

# căn nhà có garage nhưng chưa có thông tin chất lượng garage
all_data[(all_data['GarageArea'] > 0) & (all_data['GarageQual'].isnull())][['GarageType','GarageYrBlt', 'GarageFinish', 'GarageCars', 'GarageArea', 'GarageQual', 'GarageCond']]

all_data.loc[2124, 'GarageQual'] = all_data[(all_data['GarageArea'] > 355) & (all_data['GarageArea'] < 365)]['GarageQual'].mode()[0]

# trường LotFrontage: set các trường thiếu bằng giá trị trung bình trong cùng một khu phố
all_data["LotFrontage"] = all_data.groupby("Neighborhood")["LotFrontage"].transform(
  lambda x: x.fillna(x.median()))

# các trường phân loại sẽ lấy giá trị xuất hiện nhiều nhất để điền vào các giá trị thiếu
for col in ('MSZoning', 'Functional', 'Electrical', 'KitchenQual', 'Exterior1st', 'Exterior2nd', 'SaleType'):
  all_data[col] = all_data[col].fillna(all_data[col].mode()[0])

# các trường còn lại thì thay giá trị thiếu bằng "None" với loại object và 0 với loại number
# với loại object
objects = []
for i in all_data.columns:
  if all_data[i].dtype == object:
    objects.append(i)
all_data.update(all_data[objects].fillna('None'))
# với loại number
numeric_dtypes = ['int16', 'int32', 'int64', 'float16', 'float32', 'float64']
numerics = []
for i in all_data.columns:
  if all_data[i].dtype in numeric_dtypes:
    numerics.append(i)
all_data.update(all_data[numerics].fillna(0))

# biến đổi box-cox các giá trị number
skew_data = all_data[numerics].apply(lambda x: skew(x)).sort_values(ascending=False)
high_skew = skew_data[skew_data > 0.5]
skew_index = high_skew.index

for i in skew_index:
    all_data[i] = boxcox1p(all_data[i], boxcox_normmax(all_data[i] + 1))

# Thêm các trường 

all_data['YrBltAndRemod']= all_data['YearBuilt']+all_data['YearRemodAdd']
all_data['TotalSF']= all_data['TotalBsmtSF'] + all_data['1stFlrSF'] + all_data['2ndFlrSF']

all_data['Total_sqr_footage'] = (all_data['BsmtFinSF1'] + all_data['BsmtFinSF2'] +
                                 all_data['1stFlrSF'] + all_data['2ndFlrSF'])

all_data['Total_Bathrooms'] = (all_data['FullBath'] + (0.5 * all_data['HalfBath']) +
                               all_data['BsmtFullBath'] + (0.5 * all_data['BsmtHalfBath']))

all_data['Total_porch_sf'] = (all_data['OpenPorchSF'] + all_data['3SsnPorch'] +
                              all_data['EnclosedPorch'] + all_data['ScreenPorch'] +
                              all_data['WoodDeckSF'])

all_data['hasPool'] = all_data['PoolArea'].apply(lambda x: 1 if x > 0 else 0)
all_data['hasFence'] = all_data['Fence'].apply(lambda x: 1 if x != 'None' else 0)
all_data['has2ndFlrSF'] = all_data['2ndFlrSF'].apply(lambda x: 1 if x > 0 else 0)
all_data['hasGarage'] = all_data['GarageArea'].apply(lambda x: 1 if x > 0 else 0)
all_data['hasBsmt'] = all_data['TotalBsmtSF'].apply(lambda x: 1 if x > 0 else 0)
all_data['hasFireplace'] = all_data['Fireplaces'].apply(lambda x: 1 if x > 0 else 0)

# kiểm tra lại xem còn dữ liệu trống nào không
all_data_na = (all_data.isnull().sum() / len(all_data)) * 100
all_data_na = all_data_na.drop(all_data_na[all_data_na == 0].index).sort_values(ascending=False)
missing_data = pd.DataFrame({'Missing Ratio' :all_data_na})
missing_data.head()

all_data = pd.get_dummies(all_data).reset_index(drop=True)

# lọc ra thuộc tính, giá trị (SalePrice) của tập train và test
X_train = all_data[:ntrain]
X_test = all_data[ntrain:]

kfolds = KFold(10, shuffle=True, random_state=42).get_n_splits(X_train.values)
def rmsle(y, y_pred):
  return np.sqrt(mean_squared_error(y, y_pred))

def cv_rmse(model):
  rmse= np.sqrt(-cross_val_score(model, X_train.values, Y_train.values, scoring="neg_mean_squared_error", cv = kfolds))
  return(rmse)

# lasso
l_alphas = [5e-5, 0.0001, 0.0002, 0.0003, 0.0004, 0.0005, 0.0006, 0.0007, 0.0008]
lasso = make_pipeline(RobustScaler(), LassoCV(max_iter=1e7, alphas=l_alphas, random_state=42, cv=kfolds))

# ridge
alphas_ridge = [14.5, 14.6, 14.7, 14.8, 14.9, 15, 15.1, 15.2, 15.3, 15.4, 15.5]
ridge = make_pipeline(RobustScaler(), RidgeCV(alphas=alphas_ridge, cv=kfolds))

# elasticnet
e_alphas = [0.0001, 0.0002, 0.0003, 0.0004, 0.0005, 0.0006, 0.0007]
l1_ratio = [0.8, 0.85, 0.9, 0.95, 0.99, 1]
elasticnet = make_pipeline(RobustScaler(), ElasticNetCV(max_iter=1e7, alphas=e_alphas, cv=kfolds, l1_ratio=l1_ratio))

# svr
svr = make_pipeline(RobustScaler(), SVR(C= 20, epsilon= 0.008, gamma=0.0003))

# gbr
gbr = GradientBoostingRegressor(n_estimators=3000, learning_rate=0.05,
                                max_depth=4, max_features='sqrt',
                                min_samples_leaf=15, min_samples_split=10,
                                loss='huber', random_state = 42)

# xgboost
xgboost = XGBRegressor(learning_rate=0.01,n_estimators=3460,
                       max_depth=3, min_child_weight=0,
                       gamma=0, subsample=0.7,
                       colsample_bytree=0.7,
                       objective='reg:linear', nthread=-1,
                       scale_pos_weight=1, seed=27,
                       reg_alpha=0.00006)

# lightgbm
lightgbm = LGBMRegressor(objective='regression', num_leaves=4,
                         learning_rate=0.01, n_estimators=5000,
                         max_bin=200, bagging_fraction=0.75,
                         bagging_freq=5, bagging_seed=7,
                         feature_fraction=0.2,feature_fraction_seed=7,
                         verbose=-1
                        )

stack_gen = StackingCVRegressor(regressors=(lasso, elasticnet, ridge, gbr, xgboost, lightgbm),
                                meta_regressor=xgboost,
                                use_features_in_secondary=True)

# tính điểm các mô hình
score = cv_rmse(lasso)
print("Lasso score: {:.4f} ({:.4f})\n".format(score.mean(), score.std()))
score = cv_rmse(elasticnet)
print("ElasticNet score: {:.4f} ({:.4f})\n" .format(score.mean(), score.std()))
score = cv_rmse(ridge)
print("Ridge score: {:.4f} ({:.4f})\n" .format(score.mean(), score.std()))
score = cv_rmse(svr)
print("SVR score: {:.4f} ({:.4f})\n" .format(score.mean(), score.std()))
score = cv_rmse(lightgbm)
print("LightGBM score: {:.4f} ({:.4f})\n" .format(score.mean(), score.std()))
score = cv_rmse(gbr)
print("Gradient Boosting score: {:.4f} ({:.4f})\n".format(score.mean(), score.std()))
score = cv_rmse(xgboost)
print("Xgboost score: {:.4f} ({:.4f})\n".format(score.mean(), score.std()))

print('Stack_gen fitting ...')
stack_gen_model = stack_gen.fit(np.array(X_train), np.array(Y_train))

print("Lasso fitting ...")
lasso_model_full_data = lasso.fit(X_train, Y_train)

print("Elastic fitting ...")
elastic_model_full_data = lasso.fit(X_train, Y_train)

print('Ridge fitting ...')
ridge_model_full_data = ridge.fit(X_train, Y_train)

print('SVR fitting ...')
svr_model_full_data = svr.fit(X_train, Y_train)

print("GradientBoosting fitting ...")
gbr_model_full_data = gbr.fit(X_train, Y_train)

print("xgboost fitting ...")
xgb_model_full_data = xgboost.fit(X_train, Y_train)

print("lightgbm fitting ...")
lgb_model_full_data = lightgbm.fit(X_train, Y_train)

def blend_models_predict(X):
  return ((0.1 * elastic_model_full_data.predict(X)) + \
          (0.1 * lasso_model_full_data.predict(X)) + \
          (0.1 * ridge_model_full_data.predict(X)) + \
          (0.1 * svr_model_full_data.predict(X)) + \
          (0.1 * gbr_model_full_data.predict(X)) + \
          (0.15 * xgb_model_full_data.predict(X)) + \
          (0.1 * lgb_model_full_data.predict(X)) + \
          (0.25 * stack_gen_model.predict(np.array(X))))

print('RMSLE score on train data:')
print(rmsle(Y_train, blend_models_predict(X_train)))

print('Predict submission')
submission = pd.read_csv("/house-prices-advanced-regression-techniques/sample_submission.csv")
submission.iloc[:,1] = np.floor(np.expm1(blend_models_predict(X_test)))

submission.head()

submission.to_csv("/house-prices-advanced-regression-techniques/submission.csv", index=False)