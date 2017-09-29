from pyspark import SparkConf, SparkContext
from pyspark.streaming import StreamingContext
from pyspark.streaming.kafka import KafkaUtils
import operator
import numpy as np
#from set import Sets
import json
import sys
from operator import methodcaller
import random
import pyspark_cassandra
import pyspark_cassandra.streaming
from uuid import uuid1
from pyspark_cassandra import CassandraSparkContext

from pyspark.sql import SQLContext
import datetime

reload(sys)
sys.setdefaultencoding('utf-8')

#import matplotlib.pyplot as plt

def load_wordlist(filename):
    """ 
    This function returns a list or set of words from the given filename.
    """	
    words = {}
    f = open(filename, 'rU')
    text = f.read()
    text = text.split('\n')
    for line in text:
        words[line] = 1
    f.close()
    return words

def tweetwithSentiment(tweet,pwords, nwords, sterms):
    
    text = tweet.get(u'text')
    if text is not None:
         words = text.split(" ")
         sentiment = float(np.sign(sum([(1 if word in pwords else 1 if word in nwords else 0)  for word in words])))
         
         stermsBool = [sterm in words for sterm in sterms]
         # tweet = {"key": {}}
         # print(type(tweet))
         tweet["sentiment"]=sentiment
         tweet["searchTermBool"]=stermsBool
         
         #print(tweet)
         return (tweet)
         #outJson={"tweet": text, "searchTermBool":stermsBool}
         #return (outJson)
    outJson = {"tweet": "blank", "searchTermBool": 0}
    return outJson

def searchTermFunction(tweet, sterms): # give set of tuples for each tweet with each element for search term
    searchTermSentimentsLs = []
    if tweet.get(u'text') is not None:
    	for ind,sterm in enumerate(sterms):
      		if tweet.get(u"searchTermBool")[ind]:
        		searchTermSentimentsLs.append((sterm,tweet.get(u"sentiment")))   	    
    	#print(searchTermSentimentsLs)
    #searchTermSentimentsLs.append(("insertion_time","sentiment")))
    return searchTermSentimentsLs
    #return ("none",0)
def main():
    pwords = load_wordlist("./Dataset/positive.txt")
    nwords = load_wordlist("./Dataset/negative.txt")
    sterms = load_wordlist("./Dataset/keyWords.txt")
    #print(len(sterms))
    conf = SparkConf().\
        setMaster("local[2]").\
        setAppName("TweeStreamer").\
        set("spark.cassandra.connection.host",\
        "52.25.173.31, 35.165.251.179, 52.27.187.234, 52.38.246.84")
    sc = CassandraSparkContext(conf=conf)
    sc.setLogLevel("WARN")
    #sql = SQLContext(sc)
    # Creating a streaming context with batch interval of 1 sec
    ssc = StreamingContext(sc, 10)
    ssc.checkpoint("checkpoint")

    kstream = KafkaUtils.createDirectStream(
    ssc, topics = ['twitter-topic1'],
    kafkaParams = {"metadata.broker.list": 'localhost:9092'})
   
    #kstream.pprint()
    #tweets = kstream.map(lambda x: json.loads( x[1].decode('utf-8')))
    tweets = kstream.map(lambda x: json.loads( x[1]))
    tweets.count().map(lambda x:'Tweets in this batch: %s' % x).pprint() 
    tweetsUsentiment = tweets.map(lambda tweet: tweetwithSentiment(tweet, pwords, nwords, sterms))
    #tweetsUsentiment.pprint()
    #insert_time = 
    searchTermUsentiment = tweetsUsentiment.flatMap(lambda tweet: searchTermFunction(tweet, sterms)).reduceByKey(lambda a, b: a+b)
    searchTermUsentiment = searchTermUsentiment.map(lambda (key, value): {"searchterm":"_"+key, "insertion_time": datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'), "sentiment": value})
    searchTermUsentiment.pprint()
    #rddVal = sc.parallelize([{
    #	"key": "k",
    #	"stamp": 1}])
    #rddVal.pprint()
    #tweetsUsentiment.saveToCassandra("tweetdb", "tweettable") 
    searchTermUsentiment.saveToCassandra("tweetdb","searchtermtable")
    # searchTermSentiment = tweetsUsentiment.map(lambda tweet: searchTermFunction(tweet,sterms))
     
    ssc.start()
    ssc.awaitTerminationOrTimeout(1000)
    ssc.stop(stopGraceFully = True)

    

def updateFunction(newValues, runningCount):
    if runningCount is None:
       runningCount = 0
    return sum(newValues, runningCount) 


def sendRecord(record):
    connection = createNewConnection()
    connection.send(record)
    connection.close()

if __name__=="__main__":
    main()
