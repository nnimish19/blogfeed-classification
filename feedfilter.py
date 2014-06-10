import re
import naive_bayes
import feedparser
import StemmerFile
# Takes a filename of URL of a blog feed and classifies the entries
def read(feed,classifier,cat):  
    # Get feed entries and loop over them
    f=feedparser.parse(feed)
    for entry in f['entries']:
        print
        print '-----'

        #Print the contents of the entry
        print 'Title: '+entry['title'].encode('utf-8')
        #print 'Publisher: '+entry['publisher'].encode('utf-8')
        print entry['summary'].encode('utf-8')

        #Combine all the text to create one item for the classifier
        #fulltext='%s\n%s' % (entry['title'],entry['summary'])

        #Print the best guess at the current category
        #print 'Guess: '+str(classifier.classify(entry))
        print 'Training on: '+cat
        #Train on category
        classifier.train(entry,cat)  

#Takes entry(output of feedparser), returns titles as unigrams, summary words as unigrams and bigrams
def entryfeatures(entry):  #Note we call entryfeatures for classification also. So Query must be in the form of feedparser entry
    splitter=re.compile('\\W*')
    f={}
    p=StemmerFile.PorterStemmer()
    #Extract title words and annotate
    titlewords=[s.lower( ) for s in splitter.split(entry['title']) if len(s)>2 and len(s)<20]
    for w in titlewords: f['Title:'+w]=1

    #Extract summary words
    summaryword=[s.lower( ) for s in splitter.split(entry['summary']) if len(s)>2 and len(s)<20]
    #Extract root/stem of each word
    summarywords=[p.stem(s, 0,len(s)-1) for s in summaryword]
    
    #Count uppercase words
    uc=0
    for i in range(len(summarywords)):
        w=summarywords[i]
        
        f[w]=1
        if w.isupper( ): uc+=1

        # Get word pairs in summary as features
        if i<len(summarywords)-1:
            twowords=' '.join(summarywords[i:i+1])
            f[twowords]=1

    # Keep creator and publisher whole
    #f['Publisher:'+entry['publisher']]=1

    # UPPERCASE is a virtual word flagging too much shouting
    if float(uc)/len(summarywords)>0.3: f['UPPERCASE']=1

    
    return f
