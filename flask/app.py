from flask import Flask, render_template, request, redirect, session
import numpy as np
import requests
import pandas as pd
from bokeh.plotting import figure, save, output_file, vplot

app = Flask(__name__)
app.vars = {}
app.secret_key = '\t\xf7\xcc\xd1ah\xb0q*\x97\x0b\xd2pn)\x0b\xd9\xd34]R\x8c\x0b\xa5'

@app.route('/')
def main():
  return redirect('/index')

@app.route('/index')
def index():
  return render_template('index.html')

@app.route('/elfarolitosimilarities')
def similarities():
  return render_template('elfarolitosimilarities.html')

if __name__ == '__main__':
  app.run(debug=False,host='0.0.0.0')
