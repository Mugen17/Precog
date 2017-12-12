from flask import Flask, render_template
import pickle
import json
app = Flask(__name__)

@app.route('/')
def home():
	return render_template("home.html")

@app.route('/<url>')
def networkSmog(url):
	return render_template(url+'.html')

@app.route('/map')
def map():
	return render_template("map.html")

