#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Jul 24 00:53:14 2024

@author: tylerwoodall
"""
import pandas as pd

df23 = pd.read_csv('/Users/tylerwoodall/Downloads/pbp2023original.csv')
df22 = pd.read_csv('/Users/tylerwoodall/Downloads/pbp2022.csv')
df21 = pd.read_csv('/Users/tylerwoodall/Downloads/archive/pbp2021.csv')
df20 = pd.read_csv('/Users/tylerwoodall/Downloads/archive/pbp2020.csv')
df19 = pd.read_csv('/Users/tylerwoodall/Downloads/archive/pbp2019.csv')

df = pd.concat([df23, df22, df21, df20, df19], axis=0, ignore_index=True)

#remove whitespace
df['type'] = [str(x) for x in df['type']]
df['type'] = [x.strip() for x in df['type']]
df['subtype'] = [str(x) for x in df['subtype']]
df['subtype'] = [x.strip() for x in df['subtype']]
df['clock'] = [str(x) for x in df['clock']]
df['clock'] = [x.strip() for x in df['clock']]

#fill null point values with last non-null
df['h_pts'] = df['h_pts'].ffill()
df['a_pts'] = df['a_pts'].ffill()
df['h_pts'] = [int(x) for x in df['h_pts']]
df['a_pts'] = [int(x) for x in df['a_pts']]

#put time in numerical form
df['clock'] = [x.replace('PT', '')
               .replace('M','')
               .replace('S','') 
               for x in df['clock']]
df['clock'] = [float(x) for x in df['clock']]

#amend free throw rows 
df = df.drop(df[(df['subtype'] == 'Free Throw 1 of 2') 
                | (df['subtype'] == 'Free Throw 1 of 3')
                | (df['subtype'] == 'Free Throw 2 of 3')
                | (df['subtype'] == 'Free Throw Flagrant 1 of 2') 
                | (df['subtype'] == 'Free Throw Flagrant 1 of 3')
                | (df['subtype'] == 'Free Throw Flagrant 2 of 3')].index)

#drop events that aren't shots, FTs, or turnovers
df = df.drop(df[(df['type'] == 'Foul') 
                | (df['type'] == 'Substitution')
                | (df['type'] == 'Timeout')
                | (df['type'] == 'period')
                | (df['type'] == 'nan')
                | (df['type'] == 'Instant Replay')
                | (df['type'] == 'Jump Ball')
                | (df['type'] == 'Rebound')
                | (df['type'] == 'Violation')].index)

#drop remaining null team values
#may create tiny error where shot clock violations with no shots or offensive rebounds are excluded
df = df.drop(df[df['team'].isna()].index)

#create possession count column
df['poss'] = 1
df.loc[(df['subtype'] == 'Free Throw Technical') 
     & ((df['team'] != df['team'].shift(-1))
      & (df['team'] != df['team'].shift())), 'poss'] = 0

#if there's consecutive actions for 1 team, assign 0 to actions after 1st action
consecutive = df['team'] == df['team'].shift()
df.loc[consecutive, 'poss'] = 0

#create columns for point differential of every possession
df['h_diff'] = df['h_pts'].diff()
df['h_diff'] = df['h_diff'].fillna(0)
df['h_diff'] = [int(x) for x in df['h_diff']]

df['a_diff'] = df['a_pts'].diff()
df['a_diff'] = df['a_diff'].fillna(0)
df['a_diff'] = [int(x) for x in df['a_diff']]

df['point_diff'] = df['h_diff'] + df['a_diff']

#drop 4th quarter/OT plays
#df = df.drop(df[(df['period'] == 4) | (df['period'] == 5) | (df['period'] == 6)].index)

#drop rows so 1st action below 38 seconds
df = df.drop(df[(df['clock'] > 38.0)].index)

#drop possessions starting under 3 seconds unless shot made
df = df.drop(df[(df['clock'].shift() < 3)
                &(df['clock'] < 3)
                & (df['type'] != 'Made Shot')
                & (df['poss'] == 1)].index)

#create quarter_id column to group every 2 for 1 instance
df['quarter_id']= df['gameid'].astype(str) + '_' + df['period'].astype(str)

#boolean column for initiating team (takes 1st shot of 2 for 1)
#initiating shot must be taken between 28-38 seconds
df['initiating_team'] = (df['clock'] <= 38.0) & (df['clock'] >= 28.0)
df.loc[(df['initiating_team'] == True) & (df['team'] != df['team'].shift()), 'initiating_team'] = False

quarter_id = list(df['quarter_id'].drop_duplicates())

df_list = [pd.DataFrame(df.where(df['quarter_id'] == x)).dropna(how='all') for x in quarter_id]
df_list = [x.reset_index(drop=True) for x in df_list if x['initiating_team'].any()]
df_list = [x.drop(x[x['gameid'].isnull()].index) for x in df_list]

for x in df_list:
    x.loc[(x['initiating_team'] == False) & (x['team'] == x['team'][0]), 'initiating_team'] = True
    x['poss'][0] = 1
    
df2 = pd.concat(df_list)

#find average possession count and points per possessions
df3 = df2.groupby('initiating_team').agg(
    total_poss = ('poss', 'sum'),
    total_pts = ('point_diff', 'sum'))

df3['PPP'] = df3['total_pts']/df3['total_poss']
df3['avg_poss'] = df3['total_poss']/(df2['quarter_id'].drop_duplicates().count())
avg_diff = (df3['total_pts'][1] - df3['total_pts'][0])/(df2['quarter_id'].drop_duplicates().count())
print(df3)
print('average differential: ', avg_diff)
