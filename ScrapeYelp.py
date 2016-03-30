__author__ = 'natelawrence'

import time
import urllib
from bs4 import BeautifulSoup
import csv
import sys
import numpy as np

class BusinessGrid(object):
    def __init__(self,latBounds,longBounds,minReviews):
        self.latBounds = latBounds
        self.longBounds = longBounds
        self.BusinessList = []
        self.minReviews = minReviews

    def searchGrid(self):
        # search specified grid for businesses
        searchURL = lambda x: u'https://www.yelp.com/search?find_desc=restaurant&start={0}&sortby=review_count&l=g:{1},' \
                              u'{3},{2},{4}'.format(x,self.longBounds[0],self.longBounds[1],self.latBounds[0],self.latBounds[1])
        index = 0
        while index<1000:
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
                    self.review_stars.append(stars)
                    self.review_username.append(username)
                    self.review_name.append(self.name)
                index = index+20

    def saveReviews(self,filename):
        with open(filename, 'a') as csvfile:
            writer = csv.writer(csvfile, delimiter=' ')
            for ii in range(0,len(self.review_stars)):
                writer.writerow([self.review_name[ii].encode('utf-8'),self.review_username[ii].encode('utf-8'),self.review_stars[ii]])

def main():


    BizFilename = sys.argv[5]
    # ReviewFilename = sys.argv[4]
    latBounds = [sys.argv[1],sys.argv[2]]
    longBounds = [sys.argv[3],sys.argv[4]]
    minReviews = 50
    bg = BusinessGrid(latBounds,longBounds,minReviews)
    bg.searchGrid()
    print 'Found total of {} Businesses'.format(len(bg.BusinessList))
    bg.writeBusinessList(BizFilename)

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

    # load business list and get reviews
    # BizFilename = sys.argv[1]
    # ReviewFilename = sys.argv[2]
    # latBounds = [37.21,37.43]
    # longBounds = [-122.07,-122.06]
    # minReviews = 50
    # bg = BusinessGrid(latBounds,longBounds,minReviews)
    # bg.loadBusinessList(BizFilename)
    # bg.getAndSaveReviews(ReviewFilename)


if __name__ == "__main__":
    main()
