import re
import math
import naive_bayes
import feedfilter
import feedparser
import StemmerFile
from pysqlite2 import dbapi2 as sqlite


#split, convert lower_case, stemmer, stopwords, bigram
def getwords(doc):
    splitter=re.compile('\\W*') #\W* ->nonalpha(not a-zA-Z0-9)
    f={}
    porter=StemmerFile.PorterStemmer()

    words= [s.lower( ) for s in splitter.split(doc)]
    stemwords=[porter.stem(s, 0,len(s)-1) for s in words]
    docwords= [s for s in stemwords if s not in stopwords.ignorewords]
    for w in docwords: f[w]=1

    #bigram
    for i in range(len(docwords))-1:
        twowords='_'.join(docwords[i:i+2])
        f[twowords]=1

    # Return the unique set of words only
    return f #dict([(w,1) for w in words])


class classifier:    
#-----------------------------Initialize--------------------------------------
    def __init__(self,getfeatures,filename=None):
        self.fc={}  #how many times each feature has appeared in diff cat
        self.cc={}  #how many times each cat has come in training set
        self.getfeatures=getfeatures    #here we can either use getwords or more sophisticated function defined under feeedfilter, entryfeatures
        self.thresholds={}

#-----------------------------Set/Get Methods---------------------------------
    def setdb(self,dbfile):
        self.con=sqlite.connect(dbfile)
        self.con.execute('create table if not exists fc(feature,category,count)')
        self.con.execute('create table if not exists cc(category,count)')

    def flushdb(self,dbfile):
        self.con=sqlite.connect(dbfile)
        self.con.execute('drop table if exists fc')
        self.con.execute('drop table if exists cc')

    #INC Feature count
    def incf(self,f,cat):
        count=self.fcount(f,cat)
        if count==0:
            self.con.execute("insert into fc values ('%s','%s',1)" % (f,cat))
        else:
            self.con.execute("update fc set count=%d where feature='%s' and category='%s'" %(count+1,f,cat))

    #INC cat count
    def incc(self,cat):
        count=self.catcount(cat)
        if count==0:
            self.con.execute("insert into cc values ('%s',1)" % (cat))
        else:
            self.con.execute("update cc set count=%d where category='%s'"% (count+1,cat))
            
    #Get feature count
    def fcount(self,f,cat): 
        res=self.con.execute('select count from fc where feature="%s" and category="%s"'%(f,cat)).fetchone( )
        if res==None: return 0
        else: return float(res[0])    

    #Get cat count
    def catcount(self,cat):
        res=self.con.execute('select count from cc where category="%s"'%(cat)).fetchone( )
        if res==None: return 0
        else: return float(res[0])

    #List all cat
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
            
        #Inc feature count
        for f in features:
            self.incf(f,cat)
        #Inc category count
        self.incc(cat)
  

#------------------------------Classify----------------------------------
    def fprob(self,f,cat):
        if self.catcount(cat)==0: return 0
        return self.fcount(f,cat)/self.catcount(cat)

    def weightedprob(self,f,cat,prf,weight=1.0,ap=0.5):
        basicprob=prf(f,cat)
        totals=sum([self.fcount(f,c) for c in self.categories( )])
        #calculate the weighted average
        bp=((weight*ap)+(totals*basicprob))/(weight+totals)
        return bp

    #class naivebayes(classifier):
    def docprob(self,item,cat):
        #features=self.getfeatures(item)     
        #If(Feed)then getfeatures should be entryfeatures
        #else if(String) getfeatures should be getwords
        if isinstance(item, basestring): features=getwords(item)            
        else: features=self.getfeatures(item) 
        
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
        #Find the category with the highest probability
        best=default
        max=0.0
        for cat in self.categories( ):
            probs[cat]=self.prob(item,cat)
            if probs[cat]>max:
                max=probs[cat]
                best=cat
        
        #Make sure the probability exceeds threshold*next best
        for cat in probs:
            if cat==best: continue
            if probs[cat]*self.getthreshold(best)>probs[best]: return default
        return best



def sampletrain(cl):
    cl.train('Nobody owns the water.','good')
    cl.train('the quick rabbit jumps fences','good')
    cl.train('buy pharmaceuticals now','bad')
    cl.train('make quick money at the online casino','bad')
    cl.train('the quick brown fox jumps','good')
    

def rsstrain(cl):
    feedfilter.read('https://www.google.com/search?q=technology&tbm=blg&output=rss',cl, 'Technology')
    #feedfilter.read('https://www.google.com/search?q=tech%20news&tbm=blg&output=rss',cl, 'Technology')
    #feedfilter.read('https://www.google.com/search?q=latest%20gadgets&tbm=blg&output=rss',cl, 'Technology')
    #feedfilter.read('https://www.google.com/search?q=future%20technology&tbm=blg&output=rss',cl, 'Technology')
    #feedfilter.read('https://www.google.com/search?q=inspiring%20technology&tbm=blg&output=rss',cl, 'Technology')
    
    feedfilter.read('https://www.google.com/search?q=politics&tbm=blg&output=rss',cl, 'Politics')
    #feedfilter.read('https://www.google.com/search?q=indian%20politics&tbm=blg&output=rss',cl, 'Politics')
    #feedfilter.read('https://www.google.com/search?q=dirty%20politics&tbm=blg&output=rss',cl, 'Politics')
    #feedfilter.read('https://www.google.com/search?q=united%20states%20politics&tbm=blg&output=rss',cl, 'Politics')
    #feedfilter.read('https://www.google.com/search?q=world%20politics&tbm=blg&output=rss',cl, 'Politics')
    
    feedfilter.read('https://www.google.com/search?q=fashion&tbm=blg&output=rss',cl, 'Fashion')
    #feedfilter.read('https://www.google.com/search?q=fashion%20lifestyle&tbm=blg&output=rss',cl, 'Fashion')
    #feedfilter.read('https://www.google.com/search?q=casual%20wear&tbm=blg&output=rss',cl, 'Fashion')
    #feedfilter.read('https://www.google.com/search?q=party%20wear&tbm=blg&output=rss',cl, 'Fashion')
    #feedfilter.read('https://www.google.com/search?q=lifestyle&tbm=blg&output=rss',cl, 'Fashion')
    
def rssclassify(url,cl,cat):
    f=feedparser.parse(url)
    tot=0.0
    crt=0.0
    for entry in f['entries']:
        guess=str(cl.classify(entry))
        print 'Guess: '+guess
        if guess==cat: crt=crt+1
        tot=tot+1
    print 'Accuracy: '+str(crt/tot)
    return crt/tot
    
    
#cl=naive_bayes.classifier(docclass_db.getwords)
#cl.setdb('MyFile1.db')
#naive_bayes.simpletrain(cl)
#cl.fcount("quick","good")
#cl.lookup()

#Train
cl=naive_bayes.classifier(feedfilter.entryfeatures)
cl.flushdb('MyFile1.db')
cl.setdb('MyFile1.db')
naive_bayes.rsstrain(cl)

#Test
s1=rssclassify('https://www.google.com/search?q=latest%20technology&tbm=blg&output=rss',cl,'Technology')   #Technology
s2=rssclassify('https://www.google.com/search?q=current%20politics&tbm=blg&output=rss',cl,'Politics')   #Politics
s3=rssclassify('https://www.google.com/search?q=latest%20fashion&tbm=blg&output=rss',cl,'Fashion')   #Fashion

print 'Overall Accuracy: ' + str((s1+s2+s3)/3)

#http://rss.cnn.com/rss/cnn_tech.rss
