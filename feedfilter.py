import re
import naive_bayes
import feedparser
import StemmerFile
import stopwords
# Takes a filename of URL of a blog feed and classifies the entries
def read(feed,classifier,cat):  
    # Get feed entries and loop over them
    f=feedparser.parse(feed)
    for entry in f['entries']:
        #print '-----'
        #print 'Title: '+entry['title'].encode('utf-8')
        #print 'Publisher: '+entry['publisher'].encode('utf-8')
        #print entry['summary'].encode('utf-8')

        #print 'Guess: '+str(classifier.classify(entry))
        #print 'Actual : '+cat
        
        classifier.train(entry,cat)  

#Takes entry(output of feedparser), returns titles as unigrams, summary words as unigrams and bigrams
def entryfeatures(entry):  #Note we call entryfeatures for classification also. So Query must be in the form of feedparser entry
    splitter=re.compile('\\W*')
    f={}
    porter=StemmerFile.PorterStemmer()

    #Extract title words
    words= [s.lower( ) for s in splitter.split(entry['title'])]
    stemwords=[porter.stem(s, 0,len(s)-1) for s in words]
    titlewords= [s for s in stemwords if s not in stopwords.ignorewords]
    for w in titlewords: f['Title:'+w]=1
    #'Title' Specifically written because it tells that this keyword appeared in title for given cat. This differentiates it from other keywords.
    #When you do Testing, title word in feed is also appended with 'Title'. Then the category which also had this keyword in title would get more score.

    #Extract summary words
    words= [s.lower( ) for s in splitter.split(entry['summary'])]
    stemwords=[porter.stem(s, 0,len(s)-1) for s in words]
    summarywords= [s for s in stemwords if s not in stopwords.ignorewords]
    for w in summarywords: f[w]=1
    
    #bigram
    for i in range(len(summarywords)-1):
        twowords='_'.join(summarywords[i:i+1])
        f[twowords]=1

    #Keep creator and publisher whole
    #f['Publisher:'+entry['publisher']]=1
    
    #If we want to classify into other categories like-'good', 'bad' etc., we can count other features like number of capital letters used. Text written in CAPS represent shouting-hence 'bad'
    return f
