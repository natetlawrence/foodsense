from flask import Flask, render_template, request, redirect, session, url_for
import querydb
from flask_bootstrap import Bootstrap


app = Flask(__name__)
app.vars = {}
app.secret_key = '\t\xf7\xcc\xd1ah\xb0q*\x97\x0b\xd2pn)\x0b\xd9\xd34]R\x8c\x0b\xa5'

@app.route('/')
def main():
    return redirect('/top')

@app.route('/top',methods=['GET','POST'])
def top():
    #if request.method == 'GET':
        return render_template('top.html', SelectBoxTextList=querydb.getBusinessNames(None),
                               FilterBox1List=querydb.getCityNames(None),
                               FilterBox2List=querydb.getCategoryNames(None),
                               MapRestaurantName=None)
    # elif request.method == 'POST':
    #     print 'POST'
    #     app.vars['queryboxinput'] = request.form['queryboxinput']
    #     print app.vars['queryboxinput']
    #     return render_template('top.html', SelectBoxTextList=querydb.getBusinessNames(None),
    #                            MapRestaurantName=app.vars['queryboxinput'])


@app.route('/query',methods=['GET','POST'])
def query():
    if request.method == 'GET':
        return render_template('query.html', name = '/rmap')
    else:
        app.vars['rname'] = request.form['map_value']
        print app.vars['rname']
        return render_template('results.html', mapurl = '/rmap/' + app.vars['rname'].replace(' ', '%20'), name = app.vars['rname'])

@app.route('/rmap/')
@app.route('/rmap/<name>')
def rmap(name=None):
    if name:
          GJSON = querydb.getGJSON(name)
          #print unicode(GJSON).replace("'",'"')
          return render_template('rmap.html', GJSON=str(GJSON).replace("u'", "'"))
          #return render_template('rmap.html', GJSON=GJSON)
    else:
        return render_template('rmap.html', GJSON=None)

@app.route('/page/<name>')
def displaypage(name=None):
    return render_template(name)


if __name__ == '__main__':
    # load database
    Bootstrap(app)
    app.run(debug=True, host='0.0.0.0')
