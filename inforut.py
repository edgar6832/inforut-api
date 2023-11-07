from ast import Dict
from functools import wraps
from flask_cors import CORS
import pyrebase
from openpyxl.utils.dataframe import dataframe_to_rows
from openpyxl import load_workbook
from flask import Flask, jsonify, request
import pandas as pd
import numpy as np
import datetime
import warnings
import jwt
import secrets
from datetime import datetime

warnings.filterwarnings('ignore', category=UserWarning, module='openpyxl')
""" eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c3VhcmlvX2lkIjoxOSwibm9tYnJlIjoiZWRnYXI2ODMyIiwiZXhwIjpJbmZpbml0eX0.YNPMPGCpViVneuvkGTYI-3upkca1GxrSoE8CMZRBV-I """

configFirebase = {
    "apiKey": "AIzaSyAOuiUFFKIGHHI5tr_DOaNQ1S38iCPDAGg",
    "authDomain": "inforut-18f59.firebaseapp.com",
    "databaseURL": "https://inforut-18f59-default-rtdb.firebaseio.com",
    "projectId": "inforut-18f59",
    "storageBucket": "inforut-18f59.appspot.com",
    "messagingSenderId": "751622155502",
    "appId": "1:751622155502:web:d5b00b671bc739245c97ff",
}

firebase = pyrebase.initialize_app(configFirebase)
dbF = firebase.database()



app = Flask(__name__)
CORS(app)


@app.route('/inforut_api', methods=['POST'])
def upload():
    json_data = request.json
    urlFile = str(json_data.get('urlFile'))
    booking = str(json_data.get('booking'))
    user = str(json_data.get('user'))
    bookingData = dbF.child("/Gomes/Orders/"+booking).get()
    bookingData = bookingData.val()
    ##Valido si el booking existe
    if bookingData ==  None:
        response = {'message': 'Booking no registrado'}
        return jsonify(response)
    
    archivo_excel = urlFile
    df = pd.read_excel(archivo_excel, engine='openpyxl')
   
    
    response = []
    isValid = True
    data = []
    for fila, value in df.iterrows():
        driverId = str(value['driverId'])
        truckId = str(value['truckId'])
        transporterId = str(value['transporterId'])
        transporterData = dbF.child("/Gomes/Transporters/"+transporterId).get()
        transporterData = transporterData.val()        
        assignDate = str(value['date'])
        container1 = str(value['container1'])
        container2 = str(value['container2'])
        containerType = str(value['containerType'])
        scheduling = str(value['scheduling'])
        driverData = dbF.child("/Gomes/Drivers/"+driverId).get()
        driverData = driverData.val()
        truckData = dbF.child("/Gomes/Trucks/"+truckId).get()
        truckData = truckData.val()

        #valida si la fecha es válida
        if is_valid_date(assignDate) == False:
            resp = {'message': 'Fecha '+assignDate+' Inválida '+str(fila+1)}
            response.append(resp)
            isValid = False
        
        #Valida la info del transportista
        if transporterData ==  None:
            resp = {'message': 'Transportista '+transporterId+' no registrado fila '+str(fila+1)}
            response.append(resp)
            isValid = False          

        #Valida la info del conductor
        if driverData ==  None:
            resp = {'message': 'Rut '+driverId+' no registrado fila '+str(fila+1)}
            response.append(resp)
            isValid = False  
        else:          
            if transporterId != driverData['transportId']:
                resp = {'message': 'El Rut '+driverId+' no esta asociado al transportista '+driverData['transportId']+' fila: '+str(fila+1)}
                response.append(resp)
                isValid = False


        #Valida la info del camion
        if truckData ==  None:
            resp = {'message': 'Patente '+truckId+' no registrada fila '+str(fila+1)}
            response.append(resp)
            isValid = False
        else:
            if transporterId != truckData['transportId']:
                resp = {'message': 'La Patente '+truckId+' no esta asociada al transportista '+truckData['transportId']+' fila: '+str(fila+1)}
                response.append(resp)
                isValid = False
            
        if isValid:            
            item={
            'assignDate': assignDate,
            'booking': booking,
            'container1': container1,
            'container2': container2,
            'containerType': containerType,
            'destiny': bookingData['destiny'],
            'driverId': driverId,
            'driverName': driverData['name'],
            'orderId': booking,
            'origin': bookingData['origin'],
            'portingCheck': False,
            'portingPrice': 0,
            'rampId': truckData['rampId'],
            'scheduling': scheduling,
            'shippingId': bookingData['shippingId'],
            'state': 'ASIGNADO',
            'transporterId': transporterId,
            'transporterName': transporterData['companyName'],
            'truckId': truckId,
            'warehousingDays': 0,
            'warehousingPrice': 0
            }
            """ pushDatabase('Gomes/{}/{}'.format(clientId, userId), payload) """
            pushDatabase('Gomes/Orders/'+booking+'/Assigns', item, user)
            

    

    return jsonify(response)

def is_valid_date(date_string):
    try:
        # Intenta convertir la cadena en un objeto de fecha
        datetime.strptime(date_string, '%Y-%m-%d')
        return True  # La fecha es válida
    except ValueError:
        return False
    
def pushDatabase(path, object: Dict, user):   
    new = dbF.child(path).push({**object})
    object['id'] = new['name']
    dbF.child('Gomes/Assigns/'+new['name']).set({**object})    
    tracking = {
                new['name']+'1': {
                'comment': 'Asignación creada desde carga masiva',
                'createdAt': datetime.now().strftime('%Y-%m-%dT%H:%M:%S.%fZ'),
                'id': new['name']+'1',
                'orderId': object['booking'],
                'user': user
                }}
    object['Tracking'] = tracking    
    return dbF.child(path+'/'+new['name']).set({**object})

if __name__ == '__main__':
    app.run(debug=True,host='127.0.0.1', port=8080)
