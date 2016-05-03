
import json
import pandas as pd
import matplotlib.cm
import urllib
from colour import Color

dfmeta = pd.read_pickle('MetaDataFrame.pd')
simsdf = pd.read_pickle('SimilaritiesDataFrame.pd')
colors = ['#ffffcc','#ffeda0','#fed976','#feb24c','#fd8d3c','#fc4e2a','#e31a1c','#bd0026','#800026'][::-1]


def getBusinessNames(filter):
    '''
    :param filter: not supported
    :return: returns list of strings to business names matching filter
    '''
    return sorted(list(set(list(simsdf['Biz1']) + list(simsdf['Biz2']))))

def getCityNames(filter):
    '''
    :param filter: not supported
    :return: returns list of strings to city names matching filter
    '''
    return sorted(list(set(dfmeta['city'].dropna())))

def getCategoryNames(filter):
    '''
    :param filter: not supported
    :return: returns list of strings to category names matching filter
    '''
    cats = []
    for row in dfmeta['categories']:
        temp = row.split(',')
        cats.extend([item.strip() for item in temp])
    return sorted(list(set(cats)))

def parseURL(url):
    '''
    :param url: url which has been passed through rmap, contains 1 or more sections separated by +'s
                first field will be list of restaurants separated by &
                subsequent fields will be the name of field to filter on followed by = followed by list of possible
                    values separated by &
    :return: dictionary with key 'Restaurants' and value list of Restaurant names
             key 'filter' with value None if no filters or dictionary if filters are present where each key in
             dictionary is a field to filter on and value is a list of possible values
    '''
    sections = url.split('+')
    Restaurants = sections[0].split('&&')
    filters = None
    for sec in sections[1:]:
        key = sec.split('=')[0]
        value = sec.split('=')[1].split('&&')
        if filters:
            filters[key] = value
        else:
            filters = {key: value}
    return {'restaurants': Restaurants, 'filters':filters}

def getGJSON(url):
    # return the map GeoJSON for a business
    # merge all data that has an entry for biz
    url = urllib.unquote(url)
    parsedURL = parseURL(url)
    bizlist = parsedURL['restaurants']
    filters = parsedURL['filters']
    # for ind, item in enumerate(bizlist):
    #     bizlist[ind] = item.decode('utf-8')

    b = False
    bizfinal = None
    for biz in bizlist:
        biz1 = simsdf[simsdf['Biz2'] == biz].drop(['Biz2'], axis=1)
        biz1.columns = ['BizName', 'ReviewCount', 'Score']
        biz2 = simsdf[simsdf['Biz1'] == biz].drop(['Biz1'], axis=1)
        biz2.columns = ['BizName', 'ReviewCount', 'Score']
        if b:
            bizfinal = bizfinal.merge(biz1.append(biz2),on='BizName',how='outer')
        else:
            bizfinal = biz1.append(biz2)
            b = True

    scores = bizfinal.filter(regex="Score")
    reviewcounts = bizfinal.filter(regex="ReviewCount")
    meanscore = scores.mean(axis=1)
    bizfinal = bizfinal.drop(scores,axis=1)
    bizfinal = bizfinal.drop(reviewcounts,axis=1)
    bizfinal['Score'] = meanscore

    for biz in bizlist:
        if any(bizfinal['BizName'] == biz):
            bizfinal.loc[bizfinal['BizName']==biz,'Score'] = 0.0
        else:
            bizentry = pd.DataFrame([[biz, 0.0]], columns=['BizName' , 'Score'])
            bizfinal = bizfinal.append(bizentry)
    dfm = bizfinal.merge(dfmeta,on='BizName')

    if filters:
        include = [True] * len(dfm)
        for key in filters.keys():
            values = filters[key]
            for ind, row in enumerate(dfm[key]):
                if len(set(row.split(',')).intersection(set(values))) == 0:
                    include[ind] = False
        dfm = dfm[include]

    MeanScore = dfm[dfm['Score'] != 0]['Score'].mean()
    StdScore = dfm[dfm['Score'] != 0]['Score'].std()
    stdlims = [-2,2]

    bins = [i/2.0-2 for i in range(len(colors)-1)]
    zscore = (dfm['Score']-MeanScore)/StdScore
    clist = []
    for ind, item in enumerate(zscore):
        b = sum([1 if item > i else 0 for i in bins])
        clist.append(colors[b])
    dfm['Color'] = clist
    dfm.loc[dfm['Score']==0.0,'Color'] = Color('blue').hex

    # turn into a geojson file
    gjl = []
    for ind, item in dfm.iterrows():
        gj = dict()
        gj['type'] = 'Feature'
        gj['geometry'] = {'type':'Point', 'coordinates':[item['longitude'],item['latitude']]}
        desc = 'Rating Differential: '+str(round(item['Score'],2))+',\nCategories: '+item['categories']
        gj['properties'] = {'title':item['BizName'],
                            'description' : desc , 'marker-color' : item['Color'], "marker-size": "medium"}
        gjl.append(gj)
    return gjl
