from flask import Flask, render_template, request
import pandas
import pymysql
from flaskext.mysql import MySQL
from sqlalchemy import create_engine
import datetime
from dotenv import load_dotenv
import os

# load dotenv in the base root
APP_ROOT = os.path.join(os.path.dirname(__file__), '..')   # refers to application_top
dotenv_path = os.path.join(APP_ROOT, '.env')
load_dotenv(dotenv_path)

app = Flask(__name__)

mysql = MySQL()

app.config['MYSQL_DATABASE_USER'] = os.getenv('MYSQL_DATABASE_USER')
app.config['MYSQL_DATABASE_DB'] = os.getenv('MYSQL_DATABASE_DB')
app.config['MYSQL_DATABASE_PASSWORD'] = os.getenv('MYSQL_DATABASE_PASSWORD')
app.config['MYSQL_DATABASE_HOST'] = os.getenv('MYSQL_DATABASE_HOST')
mysql.init_app(app)

@app.route("/")
def hello():
    return render_template('home.html')

##Strore the name as it will be saved on the databse and the id of this record 
id_of_spreadsheet_to_table = 0
name_of_DB_table = ""

@app.route('/add_meta_data', methods=['POST', 'GET'])
def add_meta_data():
    global name_of_DB_table, id_of_spreadsheet_to_table

    if request.method == "POST":
        excel_name = request.form['excel_name'].replace(' ', '_')
        type_rust = request.form['type_rust'].replace(' ', '_')
        wheat_type = request.form['wheat_type'].replace(' ', '_')
        year = request.form['year']
        location = request.form['location'].replace(' ', '_')
        season = request.form['season'].replace(' ', '_')

        #name the table 
        name_of_table = wheat_type+"_"+type_rust+"_"+location

        #set gloables
        name_of_DB_table = name_of_table+"_"+str(datetime.datetime.now().time())

        ## add table to DB
        cursor = mysql.get_db().cursor()
        connection = mysql.get_db()
        query = "INSERT INTO Spreadsheet_to_table (excel_name, name_of_table, wheat_type, year, season, location) VALUES (%s, %s, %s, %s, %s, %s)"
        cursor.execute(query, (excel_name, name_of_DB_table, wheat_type, year, season, location))
        connection.commit()

        #save the id of the this insert 
        id_of_spreadsheet_to_table = cursor.lastrowid


        # records = cursor.fetchall()
        return render_template('home.html', added_meta_data = True)

##Store DF
uploadedDF = pandas.DataFrame()

@app.route('/upload_file', methods=['POST', 'GET'])
def upload_file():
    global uploadedDF

    if request.method == "POST":
        if '.csv' in request.files['file'].filename:
            df = pandas.read_csv(request.files['file'])
        elif '.xlsx' in request.files['file'].filename:
            df = pandas.read_excel(request.files['file'])
        else:
            return render_template('home.html', error_message= "You may only upload .csv or .xlsx files" )
        
        # save df as global var
        uploadedDF = df

        # all requared fileds
        fields = ["Plot_ID", "CID", "SID", "GID", "Variety", "Pedigree",   "Rust_Score_1", "Susceptibility_Rating_1", "Date_1",  "Rust_Score_2", "Susceptibility_Rating_2", "Date_2",  "Rust_Score_3", "Susceptibility_Rating_3", "Date_3",  "Spreadsheet"]

        return render_template('home.html', columns = df.columns.values, fields=fields, file_uploaded=True)


@app.route('/upload_file_to_db', methods=['POST', 'GET'])
def upload_file_to_db():
    global uploadedDF, name_of_DB_table, id_of_spreadsheet_to_table
    fields = ["Plot_ID", "CID", "SID", "GID", "Variety", "Pedigree",   "Rust_Score_1", "Susceptibility_Rating_1", "Date_1",  "Rust_Score_2", "Susceptibility_Rating_2", "Date_2",  "Rust_Score_3", "Susceptibility_Rating_3", "Date_3"]
    
    # query = "INSERT INTO Wheatrust.duplicateMaster_data ( Plot_ID, CID, SID, GID, Variety, Pedigree,   Rust_Score_1, Susceptibility_Rating_1, Date_1,  Rust_Score_2, Susceptibility_Rating_2, Date_2,  Rust_Score_3, Susceptibility_Rating_3, Date_3,  Spreadsheet ) VALUES(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"
    values = list()
    for field in fields:
        if request.form[field] != "None":
            #rename the selected fields to values they will be saved as 
            uploadedDF.rename(columns={request.form[field]: field}, inplace=True)
            values.append(field)
        else:
            uploadedDF[field] = None
            values.append(field)

    # ##exclude unselected columns and reorder columns  
    uploadedDF = uploadedDF[values]

    #addsheet_id
    uploadedDF['Spreadsheet_id'] = id_of_spreadsheet_to_table
    uploadedDF['Spreadsheet'] = name_of_DB_table

    #convert date columns to date data type
    uploadedDF['Date_1'] = uploadedDF['Date_1'].astype('datetime64[ns]')
    uploadedDF['Date_2'] = uploadedDF['Date_2'].astype('datetime64[ns]')
    uploadedDF['Date_3'] = uploadedDF['Date_3'].astype('datetime64[ns]')

    # # # Upload to DB
    engine = create_engine("mysql://USERNAME:DBURL/DB_NAME")
    con = engine.connect()

    # # ## Insert into master table
    uploadedDF.to_sql(name="Master_data",con=con,if_exists='append', index=False)

    ## add standalone table by name 
    uploadedDF.to_sql(name=(name_of_DB_table),con=con,if_exists='replace', index=False)
    return render_template('home.html', success_message="You table has been added! The table name is {} and the id of the spread_sheet_to_table is {}".format(name_of_DB_table, id_of_spreadsheet_to_table))
   
        
if __name__ == '__main__':
    app.run()