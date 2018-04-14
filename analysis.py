
''''
REPLACE THE BELOW PATH TO YOUR DIRECTORY
'''
%cd "Competitive Retail Intelligence"


import matplotlib
matplotlib.rcParams['backend'] = 'Qt5Agg'

import numpy as np, pandas as pd, matplotlib.pyplot as plt


prices=pd.read_csv('prices.csv') #reading input file
auditors=pd.read_csv('auditors.csv'); auditors['Full name']=auditors.First+' '+auditors.Last # creating the full name feature
stores=pd.read_json('stores.json')

prices['Banner']=prices['Store ID'].map(dict(stores[['Store ID','Banner']].values)) #fetching key "Banner" corresponding to the "Store ID"
prices['Region']=prices['Store ID'].map(dict(stores[['Store ID','Region']].values)) #fetching key "Region" corresponding to the "Store ID"

# df=prices.groupby(['Banner','UPC','Region']).mean().unstack()
df=pd.pivot_table(prices, values='Price',index=['Banner','UPC'],columns='Region') #creating a pivot table with 'Banner' and 'UPC' for rows, Region in columns and price a value
df.to_csv('output.csv') # writing the output to a csv file


ii,=np.where(prices.Banner.isna())  #looking for Nan values for the Banner ID (these corresponding 'Store ID's are not present in the json file)
prices.iloc[ii]['Store ID'].unique()
prices.iloc[ii]['Auditor ID'].map(\
    dict(auditors[['Auditor ID','Full name']].values))\
    .value_counts() #auditor responsible of the Nan values for the Banner ID (these corresponding 'Store ID's are not present in the json file)

prices.dropna(inplace=True)  #eliminating NAN values




df=pd.get_dummies(prices,columns=['Banner','Region'])  # creating dummy variables for the fields 'Banner' and 'Region' (OneHot encoder)


import statsmodels.api as sm
def regress(data, yvar, xvars):
    # this routine perform an executes a Group-wise Linear Regression, that is an ordinary least squares (OLS) regression on each chunk of data with the same UPC
    X, y, y_av = data[xvars], data[yvar], np.median(data[yvar])
    result = sm.OLS(np.log(y/y_av), X).fit()
    return result.params

# Group-wise Linear Regression (per each UPC) on the log of (Price/median(Price)) (y variable) vs. log of Region+Banner (X variable)
par=df.groupby('UPC')\
    .apply(regress, 'Price', df.keys().tolist()[5:])

par.mean(0).sort_values()  #averaging out the UPC slopes from the Group-wise Linear Regression


prices[prices.UPC==514912132] # 514912132 is the UPC of an item which contains an outlier price in Whole Foods

# this routine clean data based on the criterion that the prices must be within 3 sigma from the average (here sigma is the mean abs deviation, which is an outlier resistant estimator of the standard deviation) per each group
def clean(group,threshold):
    group['clean']=abs(group.Price - group.Price.mean()) / group.Price.mad() <= threshold
    return group

prices=prices.groupby('UPC').apply(clean,3) # cleaning the data from outlier prices
prices[~prices.clean]['Auditor ID'].map(\
    dict(auditors[['Auditor ID','Full name']].values))\
    .value_counts() # auditors responsible for outlier prices

# refitting on clean data
par=df[prices.clean].groupby('UPC').apply(regress, 'Price', df.keys().tolist()[5:])
par.mean(0).sort_values().map(lambda x: '%.1f  ' % (x*100))

# we present the pdf distribution of the group-wise fitting parameters.
fig, axes = plt.subplots(nrows=3, ncols=3, sharex=True,figsize=(12, 7))
par.apply(lambda x: 100*x).hist(ax=axes)
plt.tight_layout()
plt.xlim(-10,22)


# T-test
from scipy.stats import ttest_ind
ff=par[['Banner_Whole Foods','Banner_Safeway']].values
ttest_ind(ff[:,0],ff[:,1], equal_var=False,nan_policy='omit')


# fitting parameters that we would obtain by assuming that all the UPCs share the same slopes, rather than performing a group-wise linear regression.

def doit(group):
    group['ratio']=group.Price/group.Price.mean()
    return group

aa=df[prices.clean].groupby('UPC').apply(doit)
result = sm.OLS(np.log(aa.ratio.values), df[prices.clean][df.keys().tolist()[5:]].values).fit()
result.params[par.mean(0).argsort().values]


