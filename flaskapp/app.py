from flask import Flask, render_template, request, redirect, url_for
import querydb
from flask_bootstrap import Bootstrap


app = Flask(__name__)
app.vars = {}

@app.route('/')
def main():
    return redirect('/top')

@app.route('/top')
def top():
    return render_template('top.html', SelectBoxTextList=querydb.getBusinessNames(None),
                           FilterBox1List=querydb.getCityNames(None),
                           FilterBox2List=querydb.getCategoryNames(None),
                           MapRestaurantName=None)

@app.route('/rmap/')
@app.route('/rmap/<name>')
def rmap(name=None):
    if name:
        GJSON = querydb.getGJSON(name)
        if len(GJSON) > 0:
            return render_template('rmap.html', GJSON=str(GJSON).replace("u'", "'"))
    return render_template('rmap.html', GJSON=None)

@app.route('/page/<name>')
def displaypage(name=None):
    return render_template(name)


if __name__ == '__main__':
    # load database
    Bootstrap(app)
    app.run(debug=True, host='0.0.0.0')
