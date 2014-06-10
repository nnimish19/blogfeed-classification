import re
import math
import docclass_db
import feedfilter
import StemmerFile
from pysqlite2 import dbapi2 as sqlite


#Takes string/entry and returns unique set of words converted to lower case
def getwords(doc):
    f={}
    splitter=re.compile('\\W*') #\W* ->nonalpha(not a-zA-Z0-9)
    # Split the words by non-alpha characters
    word=[s.lower( ) for s in splitter.split(doc) if len(s)>2 and len(s)<20]

    #root words
    p=StemmerFile.PorterStemmer()
    words=[p.stem(s, 0,len(s)-1) for s in word]

    #bigram
    for i in range(len(words)):
        f[words[i]]=1;
        if i<len(words)-1:
            twowords=' '.join(words[i:i+2])
            f[twowords]=1
    # Return the unique set of words only
    return f #dict([(w,1) for w in words])


class classifier:    
#-----------------------------Initialize--------------------------------------
    def __init__(self,getfeatures,filename=None):
        # Counts of feature/category combinations
        self.fc={}
        # Counts of documents in each category
        self.cc={}
        self.getfeatures=getfeatures    #here we can either use getwords or more sophisticated function defined under feeedfilter, entryfeatures
        self.thresholds={}

#-----------------------------Set/Get Methods---------------------------------
    def setdb(self,dbfile):
        self.con=sqlite.connect(dbfile)
        self.con.execute('create table if not exists fc(feature,category,count)')
        self.con.execute('create table if not exists cc(category,count)')

    def incf(self,f,cat):
        count=self.fcount(f,cat)
        if count==0:
            self.con.execute("insert into fc values ('%s','%s',1)" % (f,cat))
        else:
            self.con.execute("update fc set count=%d where feature='%s' and category='%s'" %(count+1,f,cat))

    def incc(self,cat):
        count=self.catcount(cat)
        if count==0:
            self.con.execute("insert into cc values ('%s',1)" % (cat))
        else:
            self.con.execute("update cc set count=%d where category='%s'"% (count+1,cat))
            
    def fcount(self,f,cat): 
        res=self.con.execute('select count from fc where feature="%s" and category="%s"'%(f,cat)).fetchone( )
        if res==None: return 0
        else: return float(res[0])    

    def catcount(self,cat):
        res=self.con.execute('select count from cc where category="%s"'%(cat)).fetchone( )
        if res==None: return 0
        else: return float(res[0])

    def categories(self):
        cur=self.con.execute('select category from cc');
        return [d[0] for d in cur]

    def totalcount(self):
        res=self.con.execute('select sum(count) from cc').fetchone( );
        if res==None: return 0
        return res[0]
    def lookup(self):
        res=self.con.execute('select * from fc').fetchall( );
        print res
        print '\n'
        res=self.con.execute('select * from cc').fetchall( );
        print res
        
#-------------------------------Train------------------------------------
    def train(self,item,cat):   #item =entry if its called by read() of feedfilter we want getfeatures to be getwords
        
        if isinstance(item, basestring): features=getwords(item)    #http://stackoverflow.com/questions/1303243/how-to-find-out-if-a-python-object-a-string
        else: features=self.getfeatures(item)                       #getwords or entryfeatures function would get called depending upon what getfeatures is initialised with
            
        # Increment the count for every feature with this category
        for f in features:
            self.incf(f,cat)
        # Increment the count for this category
        self.incc(cat)
  

#------------------------------Classify----------------------------------
    def fprob(self,f,cat):
        if self.catcount(cat)==0: return 0
        # The total number of times this feature appeared in this
        # category divided by the total number of items in this category
        return self.fcount(f,cat)/self.catcount(cat)

    def weightedprob(self,f,cat,prf,weight=1.0,ap=0.5):
        # Calculate current probability
        basicprob=prf(f,cat)
    
        # Count the number of times this feature has appeared in all categories
        totals=sum([self.fcount(f,c) for c in self.categories( )])
    
        # Calculate the weighted average
        bp=((weight*ap)+(totals*basicprob))/(weight+totals)
        return bp

    #class naivebayes(classifier):
    def docprob(self,item,cat):
        #features=self.getfeatures(item)     ################################Here we are calling again feature extraction fn.this time for query (Note it depends what's the form of query(String or Feed i.e., URL).)
        #If(Feed)then getfeatures should be entryfeatures
        #else if(String) getfeatures should be getwords
        if isinstance(item, basestring): features=getwords(item)            
        else: features=self.getfeatures(item) 
        
        # Multiply the probabilities of all the features together
        p=1
        for f in features: p*=self.weightedprob(f,cat,self.fprob)
        return p

    def prob(self,item,cat):
        catprob=self.catcount(cat)/self.totalcount( )
        docprob=self.docprob(item,cat)
        return docprob*catprob

#-------------------------------------------------------------------
    def setthreshold(self,cat,t):
        self.thresholds[cat]=t

    def getthreshold(self,cat):
        if cat not in self.thresholds: return 1.0
        return self.thresholds[cat]

    def classify(self,item,default=None):
        probs={}
        # Find the category with the highest probability
        best=default
        max=0.0
        for cat in self.categories( ):
            probs[cat]=self.prob(item,cat)
            if probs[cat]>max:
                max=probs[cat]
                best=cat
        
        # Make sure the probability exceeds threshold*next best
        for cat in probs:
            if cat==best: continue
            if probs[cat]*self.getthreshold(best)>probs[best]: return default
        return best



def simpletrain(cl):
    cl.train('Nobody owns the water.','good')
    cl.train('the quick rabbit jumps fences','good')
    cl.train('buy pharmaceuticals now','bad')
    cl.train('make quick money at the online casino','bad')
    cl.train('the quick brown fox jumps','good')

def rsstrain(cl):
    feedfilter.read('https://www.google.com/search?q=technology&tbm=blg&output=rss',cl, Technology)
    feedfilter.read('https://www.google.com/search?q=politics&tbm=blg&output=rss',cl, Politics)
    feedfilter.read('https://www.google.com/search?q=fashion&tbm=blg&output=rss',cl, Fashion)
    
    
#cl=naive_bayes.classifier(docclass_db.getwords)
#cl.setdb('MyFile1.db')
#naive_bayes.simpletrain(cl)
#cl.fcount("quick","good")
#cl.lookup()

#cl=naive_bayes.classifier(feedfilter.entryfeatures)
#cl.setdb('MyFile2.db')
#naive_bayes.rsstrain(cl)
#cl.lookup()

#http://rss.cnn.com/rss/cnn_tech.rss
#http://ctrlq.org/rss/
