__author__ = 'natelawrence'

import time
import urllib
from bs4 import BeautifulSoup
import csv
import sys
import numpy as np
import json

class BusinessGrid(object):
    def __init__(self,latBounds,longBounds,minReviews):
        self.latBounds = latBounds
        self.longBounds = longBounds
        self.BusinessList = []
        self.minReviews = minReviews

    def searchGrid(self):
        # search specified grid for businesses
        searchURL = lambda x: u'https://www.yelp.com/search?find_desc=restaurant&find_loc=CA&start={0}&sortby=review_count&l=g:{1},' \
                              u'{3},{2},{4}'.format(x,self.longBounds[0],self.longBounds[1],self.latBounds[0],self.latBounds[1])
        index = 0
        while index < 1000:
            time.sleep(np.random.randint(2,7))
            print 'Searching for businesses with starting index {}'.format(index)
            html = urllib.urlopen(searchURL(index)).read()
            soup = BeautifulSoup(html)
            searchResults = soup.find_all('li',class_='regular-search-result')
            for result in searchResults:
                href = result.find('a').get('href')
                revStr = result.find('span',class_='review-count rating-qualifier').contents[0].lstrip()
                numReviews = int(revStr[:revStr.find('rev')-1])
                if numReviews<self.minReviews:
                    break
                bizName = unicode(result.find('a',class_='biz-name').find('span').contents[0])
                self.BusinessList.append(Business(bizName,href,numReviews))
            else: #if this loop exits normally then minReviews was not reached
                index = index+10
                continue #continue to next iteration of while loop, dont break it
            break

    def writeBusinessList(self,filename):
        # write businesses to file
        with open(filename, 'a') as csvfile:
            writer = csv.writer(csvfile, delimiter='\t')
            for biz in self.BusinessList:
                writer.writerow([biz.name.encode('utf-8'),biz.href,biz.numReviews])

    def loadBusinessList(self,filename):
        with open(filename, 'r') as csvfile:
            reader = csv.reader(csvfile, delimiter='\t')
            for row in reader:
                bizName = unicode(row[0].decode('utf-8'))
                href = unicode(row[1])
                numReviews = int(row[2])
                self.BusinessList.append(Business(bizName,href,numReviews))

    def getAndSaveReviews(self,filename):
        # for each business in list
        for biz in self.BusinessList:
            biz.getReviews()
            biz.saveReviews(filename)

class Business(object):
    def __init__(self,name,href,numReviews):
        self.href = href
        self.name = name
        self.numReviews = numReviews
        self.review_name = []
        self.review_username = []
        self.review_stars = []
        self.review_text = []
        self.metadata = {}


    def getReviews(self):
        # get all the reviews for a business

        try:
            print 'Getting Business reviews for {}'.format(self.name.encode('utf-8'))
        except:
            print 'Getting Next Business review. Encoding error in business name.'
        URL = lambda x: 'http://www.yelp.com'+self.href+'?start={}'.format(x)

        index = 0
        while True:
            time.sleep(np.random.randint(3,7))
            try:
                print 'Loading Reviews with index {} for {}'.format(index,self.name.encode('utf-8'))
            except:
                print 'Loading Reviews with index {}. Error encoding business name'.format(index)
            html = urllib.urlopen(URL(index)).read()
            soup = BeautifulSoup(html)

            reviews = soup.find_all("div", class_="review review--with-sidebar")
            if len(reviews)<2 or len(reviews)>self.numReviews:
                break
            else:
                reviews.pop(0) #first item in list is not a review
                for item in reviews:
                    stars = float(item.find("div",class_='review-content').find('meta').get('content'))
                    username = item.get('data-signup-object')[8:]
                    text = item.find('p').getText()
                    self.review_stars.append(stars)
                    self.review_username.append(username)
                    self.review_name.append(self.name)
                    self.review_text.append(text)
                index = index+20

    def saveReviews(self,filename):
        with open(filename, 'a') as csvfile:
            writer = csv.writer(csvfile, delimiter=' ')
            for ii in range(0,len(self.review_stars)):
                writer.writerow([self.review_name[ii].encode('utf-8'),self.review_username[ii].encode('utf-8'),
                                 self.review_stars[ii],self.review_text[ii].encode('utf-8')])

    def getmetadata(self):
        URL = 'http://www.yelp.com'+self.href
        time.sleep(np.random.randint(3,7))
        print 'Loading metadata for {}'.format(self.name.encode('utf-8'))
        html = urllib.urlopen(URL).read()
        soup = BeautifulSoup(html)

        try: #get metadata from table
            sdl = soup.find('div', class_="short-def-list")
            sdlattkeys = sdl.find_all('dt', class_="attribute-key")
            sdlattvals = sdl.find_all('dd')
            assert len(sdlattkeys) == len(sdlattvals)
            for key, val in zip(sdlattkeys, sdlattvals):
                self.metadata[key.getText().strip()] = val.getText().strip()
        except:
            print 'Error loading metadata.'

        try: #get health inspection data
            healthinsp = soup.find('dd', class_='nowrap health-score-description')
            self.metadata[u'Health Inspection Score'] = int(healthinsp.getText().strip().split(' ')[0])
        except:
            print 'Error loading health inspection score.'

        try: #get health inspection data
            pricedesc = soup.find('dd', class_='nowrap price-description')
            self.metadata[u'Price description'] = pricedesc.getText().strip()
        except:
            print 'Error loading price description.'

        try: #hours of operation
            hourstable = soup.find('table', class_='table table-simple hours-table')
            hourslist = hourstable.find_all('span', class_='nowrap')
            hl = []
            [hl.append(item.getText()) if not 'now' in item.getText() else None for item in hourslist]
            names = ['Mon Open', 'Mon Close', 'Tues Open', 'Tues Close', 'Wed Open', 'Wed Close', 'Thurs Open', 'Thurs Close', 'Fri Open', 'Fri Close', 'Sat Open', 'Sat Close', 'Sun Open', 'Sun Close']
            for key, val in zip(names, hl):
                self.metadata[key] = val
        except:
            print 'Error loading hours of operation.'

        try: # location
            lightboxmap = soup.find('div', class_='lightbox-map hidden')
            center = json.loads(lightboxmap.get('data-map-state'))['center']
            self.metadata['latitude'] = center['latitude']
            self.metadata['longitude'] = center['longitude']
        except:
            print 'Error loading location.'

        try: # get address and neighborhood
            mapbox = soup.find('li', class_='map-box-address')
            spans = mapbox.find_all('span')
            keynames = ['street address', 'city', 'state', 'zipcode', 'neighborhood']
            index = [0, 1, 2, 3, 5]
            for key, ind in zip(keynames,index):
                try:
                    self.metadata[key] = spans[ind].text.strip()
                except:
                    print 'Couldnt find {}'.format(key)
        except:
            print 'Error loading neighborhood.'

        try: # cuisine type
            catlist = soup.find('span', class_='category-str-list')
            cats = catlist.find_all('a')
            categories = {}
            for cat in cats:
                categories[cat.text] = 1
            self.metadata['categories'] = categories
        except:
            print 'Error loading location.'

    def savemetadata(self, filename):
        # append metadata to file
        self.metadata['BizName'] = self.name.encode('utf-8')
        self.metadata['href'] = self.href
        self.metadata['NReviews'] = self.numReviews
        with open(filename, 'a') as jsonfile:
            json.dump(self.metadata, jsonfile)
            jsonfile.write('\n')

def saveListMetaData(BListFileName,MetaDataFileName):
    # input filename containing list of businesses, fetch metadata for eacha nd save to file
    bg = BusinessGrid([None,None],[None,None],None)
    bg.loadBusinessList(BListFileName)
    for b in bg.BusinessList:
        b.getmetadata()
        b.savemetadata(MetaDataFileName)

def main():


    # BizFilename = sys.argv[5]
    # # ReviewFilename = sys.argv[4]
    # latBounds = [sys.argv[1],sys.argv[2]]
    # longBounds = [sys.argv[3],sys.argv[4]]
    # minReviews = 50
    # bg = BusinessGrid(latBounds,longBounds,minReviews)
    # bg.searchGrid()
    # print 'Found total of {} Businesses'.format(len(bg.BusinessList))
    # bg.writeBusinessList(BizFilename)

    #
    # bg.getAndSaveReviews(ReviewFilename)

    #append all business lists into one
    # bg = BusinessGrid(latBounds,longBounds,minReviews)
    # numInstance = 15
    #
    # BizFilename = lambda start,stop: 'YelpBusinessList5_{}_{}.csv'.format(start,stop)
    # blockLimits = [0,30]
    # step = (blockLimits[1]-blockLimits[0])/float(numInstance)
    # blockStart = list(np.round(np.arange(blockLimits[0],blockLimits[1]-step+.001,step)).astype(int))
    # blockStop = list(np.round(np.arange(blockLimits[0]+step,blockLimits[1]+.001,step)).astype(int))
    #
    # for bb in range(0,numInstance):
    #     bg.loadBusinessList(BizFilename(blockStart[bb],blockStop[bb]))
    # bg.writeBusinessList('BusinessList.csv')

    ## load business list and get reviews
    # BizFilename = sys.argv[1]
    # ReviewFilename = sys.argv[2]
    # latBounds = [None,None]
    # longBounds = [None,None]
    # minReviews = None
    # bg = BusinessGrid(latBounds,longBounds,minReviews)
    # bg.loadBusinessList(BizFilename)
    # bg.getAndSaveReviews(ReviewFilename)

    ## test get metadata
    # b = Business('Taqueria','/biz/taqueria-castillo-mason-san-francisco',100)
    # b.getmetadata()
    # b.savemetadata('TaqueriaMetaData.json')

    mode = sys.argv[1]
    if mode == '0':
        BizFilename = sys.argv[5]
        # ReviewFilename = sys.argv[4]
        latBounds = [sys.argv[1],sys.argv[2]]
        longBounds = [sys.argv[3],sys.argv[4]]
        minReviews = 100
        bg = BusinessGrid(latBounds,longBounds,minReviews)
        bg.searchGrid()
        print 'Found total of {} Businesses'.format(len(bg.BusinessList))
        bg.writeBusinessList(BizFilename)
    elif mode == '1':
        ## run to save metadata from filename input
        BListFileName, MetaDataFileName = sys.argv[2], sys.argv[3]
        saveListMetaData(BListFileName, MetaDataFileName)
    elif mode == '2':
        ## load business list and get reviews
        BizFilename = sys.argv[2]
        ReviewFilename = sys.argv[3]
        latBounds = [None,None]
        longBounds = [None,None]
        minReviews = None
        bg = BusinessGrid(latBounds,longBounds,minReviews)
        bg.loadBusinessList(BizFilename)
        bg.getAndSaveReviews(ReviewFilename)

if __name__ == "__main__":
    main()
