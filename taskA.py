import tweepy
from pymongo import MongoClient
import pycountry
import pygal
import pickle
import csv
import plotly
import plotly.plotly as py
import plotly.graph_objs as go
import matplotlib.pyplot as plt
import operator
import numpy as np
from textblob import TextBlob

client = MongoClient()
precog = client.precog
smog = precog.smog
rain = precog.rain

consumerKey = ''
consumerSecret = ''
accessToken = ''
accessTokenSecret = ''

auth = tweepy.AppAuthHandler(consumerKey, consumerSecret)

api = tweepy.API(auth, wait_on_rate_limit=True, wait_on_rate_limit_notify=True)

smogHashtags = ['#SmogInDelhi','#DelhiSmog','#Smog','#CropBurning','#MyRightToBreathe']
rainHashtags = ['#MumbaiRains','#CycloneOckhi','#Ockhi''#Mumbai']

def collect():	
	tweets = tweepy.Cursor(api.search, q = '#Mumbai').items(5000)
	for tweet in tweets:
		rain.insert_one(tweet._json)

def removeDuplicates():
	tweets = []
	for tweet in rain.find():
		if(tweet['id'] not in tweets):
			tweets.append(tweet['id'])
		else:
			smog.delete_one({"_id": tweet['_id']})

def makeCountries():
	countries = {}
	for i in range(0,len(pycountry.countries)):							#Making a list of countries from pycountry to use to check for location of tweets and user
		countries[list(pycountry.countries)[i].name.lower()] = 0
	return countries


def getCountries(collection):
	countries = {}
	countryList = makeCountries()
	countries['Unidentifiable'] = 0											#Creating an unidentifiable category to categorize all the tweets 
	total = 0																#which dont have valid information on location
	timezones = []
	#countries = makeCountries()
	for tweet in collection.find():
		total = total + 1
		try:
			if(tweet['place']['country'].lower() not in countries.keys()):	#Checking if the place of the tweet is a valid country
				countries[str(tweet['place']['country'].lower())] = 1
			else:
				countries[str(tweet['place']['country'].lower())] = countries[str(tweet['place']['country'].lower())] + 1
		except:
			try:
				if(tweet['user']['location'].lower() in countryList):
					if(tweet['user']['location'].lower() not in countries.keys()): 	#checking if user location is a valid country
						countries[str(tweet['user']['location'].lower())] = 1
					else:
						countries[str(tweet['user']['location'].lower())] =  countries[str(tweet['user']['location'].lower())] + 1
				else:
					countries['Unidentifiable'] = countries['Unidentifiable'] + 1	#put the rest under unidentifiable category. Could use the timezone 
			except:																	#but there are many unique timezones. Could be updated later
				countries['Unidentifiable'] = countries['Unidentifiable'] + 1

	pieCountry = pygal.Pie()
	pieCountry.title = "Countries of tweets in %"
	for x in countries.keys():
		pieCountry.add(x,float(countries[x]*100/float(total)))
	pieCountry.render_to_file('country.svg')

	forMap = {}																		#Interactive map to give a better idea of the concentration of tweets
	for i in pycountry.countries:													#Could be inaccurate though due to the abundance of unidentifiable locations
		code  = i.alpha_2.lower()
		forMap[i.name.lower()] = code
	temp = list(countries.keys())
	for i in temp:
		try:
			countries[forMap[i]] = countries.pop(i)
		except:
			pass
	map = pygal.maps.world.World()
	map.title = 'No. of Tweets'
	map.add('Tweets', countries)
	map.render_to_file('mapRain.svg')
	with open('mapRain.csv','w') as f:
		w = csv.writer(f)
		for key, value in countries.items():
			w.writerow([key,value])

def getUsers():
	users = []
	check = []
	count = 0
	for tweet in smog.find():
		if(tweet['in_reply_to_screen_name']):
			count = count + 1
		temp = {}
		userid = tweet['user']['screen_name']
		if(userid not in check):
			check.append(userid)
			temp['name'] = userid
			temp['x'] = 1
			temp['y'] = 1
			users.append(temp)

def getTopHashtags(collection):
	hashtags = []
	dictionary = {}
	for tweet in collection.find():
		for hashtag in tweet['entities']['hashtags']:
			tag = hashtag['text']
			hashtags.append(str(hashtag['text'].encode('utf-8')))
			if(tag not in dictionary.keys()):
				dictionary[tag] = 1
			else:
				dictionary[tag] = dictionary[tag] + 1
	i = 0
	finalWords = []
	finalCount = []
	sortedWords = sorted(dictionary.items(),key = operator.itemgetter(1))
	for x in reversed(sortedWords):
		finalWords.append(x[0])
		finalCount.append(x[1])
		if(i==20):
			break
		i = i + 1

	colors = ['#696969']
	trace = go.Bar(x = finalWords, y = finalCount, marker =  dict(color = '#696969'))
	data = [trace]
	fig = go.Figure(data = data)
	plotly.offline.plot(fig, filename = 'hashtagsRain')

	answer = ''.join(hashtags)
	with open("hashtags.txt", "w") as text_file:
		print(f"{hashtags}", file=text_file)

def getOriginalVsRetweet(collection):
	total = 0
	original = 0
	retweet = 0
	for tweet in collection.find():
		total = total + 1
		text = tweet['text']
		if(text[0] == 'R' and text[1] == 'T' and text[3] == '@'):
			retweet = retweet + 1
		else:
			original = original + 1
	#print(total, original, retweet)
	labels = ['Original','Retweet']
	values = [original, retweet]
	colors = ['#696969','#A9A9A9']
	layout = go.Layout(title = "Delhi Smog")
	trace = go.Pie(labels = labels, values = values, marker = dict(colors = colors))
	fig = go.Figure(data = [trace], layout = layout)
	plotly.offline.plot(fig, filename = 'OriginalVsRetweetSmog')

def getFavouriteCount(collection):
	count = []
	labels = []
	for tweet in collection.find():
		count.append(tweet['favorite_count'])
		labels.append(tweet['id_str'])

	#x = np.arange(len(labels))
	#y = np.asarray(count)
	#my_xticks = labels
	#plt.xticks(x, my_xticks, rotation = 90)
	#plt.plot(x, y)
	#plt.show()
	trace = go.Scatter(x = labels, y = count, mode = 'markers')
	data = [trace]
	plotly.offline.plot(data, filename = 'favouriteCountRain.html')

def getTweetImage(collection):
	text = 0
	image = 0
	textAndImage = 0
	for tweet in collection.find():
		flagImage = 0
		flagText = 0 
		if('media' in tweet['entities']):
			flagImage = 1
			if(len(tweet['text'].split())>len(tweet['extended_entities']['media'])):
				flagText = 1
		else:
			flagText = 1
		if(flagImage == 1 and flagText == 0):
			image = image + 1
		if(flagText == 1 and flagImage == 0):
			text = text + 1
		else:
			textAndImage = textAndImage + 1
	print(text, image, textAndImage)

def getDiscussions():
	total = 0
	count = 0
	for tweet in smog.find():
		if(tweet['place']):
			total = total + 1
			if(tweet['place']['name'] == 'New Delhi'):
				count = count + 1
	print(total,count)


def plotHori():
	trace1 = go.Bar(y = ['Delhi Smog','Mumbai Rains'], x = [51,388], name = 'In Delhi/Mumbai', orientation = 'h', marker = dict(color = '#696969'))
	trace2 = go.Bar(y = ['Delhi Smog','Mumbai Rains'], x = [249-51,604-388], name = 'Outside', orientation = 'h', marker = dict(color = '#A9A9A9'))
	data = [trace1, trace2]
	layout = go.Layout(barmode = 'stack')
	fig = go.Figure(data = data, layout = layout)
	plotly.offline.plot(fig, filename = 'getDiscussions.html')

def tweetSentiment():
	smogPos = 0
	smogNeg = 0
	rainPos = 0
	rainNeg = 0
	for tweet in smog.find():
		text = tweet['text']
		ans =TextBlob(text)
		if(ans.sentiment.polarity>=0):
			smogPos = smogPos + 1
		else:
			smogNeg = smogNeg + 1
	for tweet in rain.find():
		text = tweet['text']
		ans = TextBlob(text)
		if(ans.sentiment.polarity>=0):
			rainPos = rainPos + 1
		else:
			rainNeg = rainNeg + 1
	trace1 = go.Bar(x = ['Delhi Smog','Mumbai Rains'], y = [smogPos,rainPos], name = 'Positive', marker = dict(color = '#696969'))
	trace2 = go.Bar(x = ['Delhi Smog','Mumbai Rains'], y = [smogNeg,rainNeg], name = 'Negative', marker = dict(color = '#A9A9A9'))
	data = [trace1, trace2]
	layout = go.Layout(barmode = 'group')
	fig = go.Figure(data = data, layout = layout)
	plotly.offline.plot(fig, filename = 'tweetSentiment.html')

def favSentiment():
	smogPos = 0
	smogPosFav = 0
	smogNeg = 0
	smogNegFav = 0
	rainPos = 0
	rainPosFav = 0
	rainNeg = 0
	rainNegFav = 0
	for tweet in smog.find():
		text = tweet['text']
		ans =TextBlob(text)
		if(ans.sentiment.polarity>=0):
			smogPos = smogPos + 1
			smogPosFav = smogPosFav + tweet['favorite_count']
		else:
			smogNeg = smogNeg + 1
			smogNegFav = smogNegFav + tweet['favorite_count']
	for tweet in rain.find():
		text = tweet['text']
		ans = TextBlob(text)
		if(ans.sentiment.polarity>=0):
			rainPos = rainPos + 1
			rainPosFav = rainPosFav + tweet['favorite_count']
		else:
			rainNeg = rainNeg + 1
			rainNegFav = rainNegFav + tweet['favorite_count']
	print(smogPosFav/float(smogPos))
	print(smogNegFav/float(smogNeg))
	print(rainPosFav/float(rainPos))
	print(rainNegFav/float(rainNeg))

def totalVals():
	smogTweets = 0
	smogFavs = 0
	smogRetweets = 0
	smogUsers = []
	smogHashtags = []
	rainTweets = 0
	rainFavs = 0
	rainRetweets = 0
	rainUsers = []
	rainHashtags = []
	for tweet in smog.find():
		smogTweets = smogTweets + 1
		if(tweet['user']['id'] not in smogUsers):
			smogUsers.append(tweet['user']['id'])
		smogFavs = smogFavs + tweet['favorite_count']
		smogRetweets = smogRetweets + tweet['retweet_count']
		for hashtag in tweet['entities']['hashtags']:
			tag = hashtag['text']
			if(tag not in smogHashtags):
				smogHashtags.append(tag)
	for tweet in rain.find():
		rainTweets = rainTweets + 1
		if(tweet['user']['id'] not in rainUsers):
			rainUsers.append(tweet['user']['id'])
		rainFavs = rainFavs + tweet['favorite_count']
		rainRetweets = rainRetweets + tweet['retweet_count']
		for hashtag in tweet['entities']['hashtags']:
			tag = hashtag['text']
			if(tag not in rainHashtags):
				rainHashtags.append(tag)

	print(smogTweets)
	print(smogFavs)
	print(smogRetweets)
	print(len(smogUsers))
	print(len(smogHashtags))
	print(rainTweets)
	print(rainFavs)
	print(rainRetweets)
	print(len(rainUsers))
	print(len(rainHashtags))

def makeGraph():
	i = 1
	users = {}
	links = {}
	for tweet in rain.find():
		if(tweet['user']['id'] not in users):
			users[tweet['user']['id']] = i
			i = i + 1
		for x in tweet['entities']['user_mentions']:
			if(x['id'] not in users):
				users[x['id']] = i
				i = i + 1
				links[users[tweet['user']['id']]] = users[x['id']]
	with open('userNodesRain.csv','w') as f:
		w = csv.writer(f)
		for key, value in users.items():
			w.writerow([key,value])
	with open('userEdgesRain.csv','w') as f:
		w = csv.writer(f)
		for key, value in links.items():
			w.writerow([key,value])

getCountries(rain)