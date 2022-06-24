import pandas as pd
from django.shortcuts import render
from django.http import HttpResponse
from .forms import VroomForm
from .forms import VroomForm2
from django.views.generic import TemplateView
import requests
import json
from pandas.io.json import json_normalize
import random
import numpy as np
import math

class VroomView(TemplateView):
    def __init__(self):
        None

    def get(self, request):
        params = {
            'form': VroomForm(),
            'resultFlg' : False,
            'error_msg' : '',
            }
        return render(request, 'vroom/index.html', params)

    def post(self, request):

        try:
            form = VroomForm(request.POST, request.FILES)
            if form.is_valid():
                try:
                    shipments_file = request.FILES['shipments_file']
                    vehicles_file = request.FILES['vehicles_file']
    
                    shipments = pd.read_csv(shipments_file)
                    vehicles = pd.read_csv(vehicles_file)

                    address_dict_p = {}
                    address_dict_d = {}
                    if '集荷住所' in shipments.columns and '配送先住所' in shipments.columns:
                        for index, row in shipments.iterrows():
                            address_dict_p[row['ID']] = row['集荷住所']
                            address_dict_d[row['ID']] = row['配送先住所']

                    company_name_dict = {}
                    if '会社名' in shipments.columns:
                        for index, row in shipments.iterrows():
                            company_name_dict[row['ID']] = row['会社名']


                    shipments_original = shipments
                    vehicles_original = vehicles
                    

                    shipments = shipments.fillna(0)
                    shipments[['容積', '重さ', 'スキル(冷凍)','積上時間(分)','積下時間(分)', 'スキル(危険)', 'スキル(冷蔵)']] = shipments[['容積', '重さ', 'スキル(冷凍)','積上時間(分)','積下時間(分)', 'スキル(危険)', 'スキル(冷蔵)']].astype(np.int64)
                    shipments[['集荷可能時間帯①(開始)', '集荷可能時間帯①(終了)','集荷可能時間帯②(開始)', '集荷可能時間帯②(終了)']] = (shipments[['集荷可能時間帯①(開始)', '集荷可能時間帯①(終了)','集荷可能時間帯②(開始)', '集荷可能時間帯②(終了)']]*3600).astype(np.int64)
                    shipments[['配送可能時間帯①(開始)', '配送可能時間帯①(終了)','配送可能時間帯②(開始)', '配送可能時間帯②(終了)']] = (shipments[['配送可能時間帯①(開始)', '配送可能時間帯①(終了)','配送可能時間帯②(開始)', '配送可能時間帯②(終了)']]*3600).astype(np.int64)

                    vehicles = vehicles.fillna(0)
                    vehicles[['積載可能容積', '積載可能重量', 'スキル(冷凍)', 'スキル(危険)', 'スキル(冷蔵)']] = vehicles[['積載可能容積', '積載可能重量', 'スキル(冷凍)', 'スキル(危険)', 'スキル(冷蔵)']].astype(np.int64)
                    vehicles[['稼働時間(開始)','稼働時間(終了)']] = (vehicles[['稼働時間(開始)','稼働時間(終了)']]*3600).astype(np.int64)



                    input_json = '{ "vehicles": ['
                    for index, vehicle in vehicles.iterrows():
                        skills = []
                        if vehicle['スキル(冷凍)'] > 0.5:
                            skills.append(1)
                        if vehicle['スキル(危険)'] > 0.5:
                            skills.append(2)
                        if vehicle['スキル(冷蔵)'] > 0.5:
                            skills.append(3)
                        input_json += ' { '
                        input_json += ' "id": {},'.format(int(vehicle['ID']))
                        input_json += ' "start": [ {} , {} ],'.format(vehicle['出発地経度'],vehicle['出発地緯度'])
                        input_json += ' "end": [ {} , {} ],'.format(vehicle['到着地経度'],vehicle['到着地緯度'])
                        input_json += ' "time_window": [ {},{} ],'.format(vehicle['稼働時間(開始)'],vehicle['稼働時間(終了)'])
                        input_json += ' "skills": {},'.format(skills)
                        input_json += ' "capacity": [ {}, {} ]'.format(vehicle['積載可能容積'],vehicle['積載可能重量'])
                        input_json += ' }'
                        if index != len(vehicles)-1:
                            input_json += ','

                    input_json += ' ],'

                    input_json += ' "shipments": ['
                    for index, shipment in shipments.iterrows():
                        skills = []
                        if shipment['スキル(冷凍)'] > 0.5:
                            skills.append(1)
                        if shipment['スキル(危険)'] > 0.5:
                            skills.append(2)
                        if shipment['スキル(冷蔵)'] > 0.5:
                            skills.append(3)
                        input_json += ' { '
                        input_json += ' "amount": [ {}, {} ],'.format(shipment['容積'],shipment['重さ'])
                        input_json += ' "skills": {},'.format(skills)
                        if shipment['集荷可能時間帯②(開始)'] == 0 and shipment['集荷可能時間帯②(終了)'] == 0:
                            input_json += ' "pickup": {{ "id": {} , "service": {}, "location": [ {} , {} ], "time_windows": [[ {}, {}]] }},'.format(int(shipment['ID']),shipment['積上時間(分)']*60,shipment['集荷経度'],shipment['集荷緯度'],shipment['集荷可能時間帯①(開始)'],shipment['集荷可能時間帯①(終了)'])
                        else:
                            input_json += ' "pickup": {{ "id": {} , "service": {}, "location": [ {} , {} ], "time_windows": [[ {}, {},{}, {} ]] }},'.format(int(shipment['ID']),shipment['積上時間(分)']*60,shipment['集荷経度'],shipment['集荷緯度'],shipment['集荷可能時間帯①(開始)'],shipment['集荷可能時間帯①(終了)'],shipment['集荷可能時間帯②(開始)'],shipment['集荷可能時間帯②(終了)'])
                            
                        if shipment['配送可能時間帯②(開始)'] == 0 and shipment['配送可能時間帯②(終了)'] == 0:
                            input_json += ' "delivery": {{ "id": {} , "service": {}, "location": [ {} , {} ], "time_windows": [[ {}, {}]] }}'.format(int(shipment['ID']),shipment['積下時間(分)']*60,shipment['配送先経度'],shipment['配送先緯度'],shipment['配送可能時間帯①(開始)'],shipment['配送可能時間帯①(終了)'])
                        else:
                            input_json += ' "delivery": {{ "id": {} , "service": {}, "location": [ {} , {} ], "time_windows": [[ {}, {},{}, {} ]] }}'.format(int(shipment['ID']),shipment['積下時間(分)']*60,shipment['配送先経度'],shipment['配送先緯度'],shipment['配送可能時間帯①(開始)'],shipment['配送可能時間帯①(終了)'],shipment['配送可能時間帯②(開始)'],shipment['配送可能時間帯②(終了)'])
                        input_json += ' }'
                        
                        if index != len(shipments)-1:
                            input_json += ','

                    input_json += ']}'
                except Exception as e:
                    print(e)
                    error_msg = 'CSVファイルが不正です。:' + str(e)
                    params = {
                        'form': VroomForm(),
                        'resultFlg' : False,
                        'error_msg' : error_msg,
                        }
                    return render(request, 'vroom/index.html', params)
                print(input_json)
    
            headers = {
                'Content-type': 'application/json',
                }
                
            response = requests.post('http://10.0.2.20:5000/', headers=headers, data=input_json)
    
            result = response._content.decode()
            result_json = json.loads(result)
#            print(json.dumps(result_json, indent=2))
            print(result_json)
    
            summary_html = json_normalize(result_json).reset_index().drop('unassigned', axis=1).drop('routes', axis=1).to_html(index = False, classes='table table-striped')
            
            if len(result_json['unassigned']) > 0:
                unassigned = json_normalize(result_json['unassigned']).sort_values(by=['id','type'],ascending=[True,False]).reset_index().drop('index', axis=1)
            else:
                unassigned = pd.DataFrame(result_json['unassigned'])

            unassigned['address'] = ''
            unassigned['company'] = ''
            if '集荷住所' in shipments.columns and '配送先住所' in shipments.columns:
                for index, row in unassigned.iterrows():
                    if row['type'] == 'pickup':
                        unassigned.loc[index,'address'] = address_dict_p[int(row['id'])]
                    elif row['type'] == 'delivery':
                        unassigned.loc[index,'address'] = address_dict_d[int(row['id'])]

            if '会社名' in shipments.columns:
                for index, row in unassigned.iterrows():
                    if not np.isnan(row['id']):
                        unassigned.loc[index,'company'] = company_name_dict[int(row['id'])]


            routes = result_json['routes']
            route_htmls = []
            route_csvs = []
            script_html = '<script>function initMap() {'
            colors = ['#ff0000','#ff007f','#ff00ff','#7f00ff','#0000ff','#007fff','#00ffff','#00ff7f','#00ff00','#7fff00','#ff7f00']
            for index, route in enumerate(routes):
                map_html = '<div id="map' + str(route["vehicle"]) + '" style="width:800px; height:800px"></div>'
                df_steps = json_normalize(route['steps'])
                df_steps['time'] = df_steps['arrival'].map(to_h_m_s)
                df_steps['address'] = ''
                df_steps['company'] = ''
                if '集荷住所' in shipments.columns and '配送先住所' in shipments.columns:
                    for index, row in df_steps.iterrows():
                        if row['type'] == 'pickup':
                            df_steps.loc[index,'address'] = address_dict_p[int(row['id'])]
                        elif row['type'] == 'delivery':
                            df_steps.loc[index,'address'] = address_dict_d[int(row['id'])]

                if '会社名' in shipments.columns:
                    for index, row in df_steps.iterrows():
                        if not np.isnan(row['id']):
                            df_steps.loc[index,'company'] = company_name_dict[int(row['id'])]

                route_htmls.append((route['vehicle'], json_normalize(route).drop('steps', axis=1).to_html(index = False, classes='table table-striped'), df_steps.to_html(classes='table table-striped'),map_html))
                route_csvs.append(df_steps.to_csv(index = False))
                script_html += 'var opts' + str(route['vehicle']) + ' = {zoom: 13,center: new google.maps.LatLng(' + str(route['steps'][0]['location'][1]) + ',' +  str(route['steps'][0]['location'][0]) + ')};'
                script_html += 'var map' + str(route['vehicle']) + '  = new google.maps.Map(document.getElementById("map' + str(route['vehicle']) + '"), opts' + str(route['vehicle']) + ' );'
                script_html += 'var flightPlanCoordinates' + str(route['vehicle']) + ' = [ '
                for step in route['steps']:
                    script_html += 'new google.maps.LatLng(' + str(step['location'][1]) + ',' +  str(step['location'][0]) + '),'
                script_html += '];'
                script_html += 'var flightPath' + str(route['vehicle']) + ' = new google.maps.Polyline({path: flightPlanCoordinates' + str(route['vehicle']) + ','
                script_html += 'strokeColor: "' + colors[random.randint(0,len(colors)-1)] + '", strokeOpacity: 1.0, strokeWeight: 5 });'
                script_html += 'flightPath' + str(route['vehicle']) + '.setMap(map' + str(route['vehicle'])  + ' );'
                script_html += '    var markerData' + str(route['vehicle']) + ' = ['
                for step in route['steps']:
                    script_html += '        { lat:"' + str(step['location'][1]) + '", lng:"' + str(step['location'][0]) + '", title:"type:' + step['type'] + ','  + 'arrival:' + to_h_m_s(step['arrival']) + ',' + 'service:' + to_h_m_s(step['service']) + ',' + 'duration:' + str(step['duration']) + ',' + 'load:' + str(step['load'])  + '" },'
                script_html += '    ];'
                script_html += '    for (i = 0;i < markerData' + str(route['vehicle']) + '.length;i++) {'
                script_html += 'if ( i == 0 || i == markerData' + str(route['vehicle']) + '.length - 1) {'
                script_html += '        var marker = new google.maps.Marker({'
                script_html += '            position: new google.maps.LatLng(markerData' + str(route['vehicle']) + '[i].lat, markerData' + str(route['vehicle']) + '[i].lng),'
                script_html += '            icon: {  fillColor: "#FF00FF",  fillOpacity: 0.8,  path: google.maps.SymbolPath.CIRCLE,  scale: 16,  strokeColor: "#FF0000",  strokeWeight: 1.0 }, label: {  text:  String(i)  ,  color: "#FFFFFF",  fontSize: "20px" },'
                script_html += '            title: markerData' + str(route['vehicle']) + '[i].title'
                script_html += '        });'
                script_html += '} else if ( markerData' + str(route['vehicle']) + '[i].title' + '.match(/pickup/)) {'
                script_html += '        var marker = new google.maps.Marker({'
                script_html += '            position: new google.maps.LatLng(markerData' + str(route['vehicle']) + '[i].lat, markerData' + str(route['vehicle']) + '[i].lng),'
                script_html += '            icon: {  fillColor: "#FF0000",  fillOpacity: 0.8,  path: google.maps.SymbolPath.CIRCLE,  scale: 16,  strokeColor: "#FF0000",  strokeWeight: 1.0 }, label: {  text:  String(i)  ,  color: "#FFFFFF",  fontSize: "20px" },'
                script_html += '            title: markerData' + str(route['vehicle']) + '[i].title'
                script_html += '        });'
                script_html += '} else {'
                script_html += '        var marker = new google.maps.Marker({'
                script_html += '            position: new google.maps.LatLng(markerData' + str(route['vehicle']) + '[i].lat, markerData' + str(route['vehicle']) + '[i].lng),'
                script_html += '            icon: {  fillColor: "#0000FF",  fillOpacity: 0.8,  path: google.maps.SymbolPath.CIRCLE,  scale: 16,  strokeColor: "#0000FF",  strokeWeight: 1.0 }, label: {  text:  String(i)  ,  color: "#FFFFFF",  fontSize: "20px" },'
                script_html += '            title: markerData' + str(route['vehicle']) + '[i].title'
                script_html += '        });'
                script_html += '} '

                script_html += '        marker.setMap(map' + str(route['vehicle'])  + ');'
                script_html += '    }'
            script_html += '}</script>'

            google_script_html = '<script async defer  src="https://maps.googleapis.com/maps/api/js?key=AIzaSyAbBWy9eBi2VI1j5nC82yPN1I7hBMu9fvk&callback=initMap"></script>'
    
            params = {
                'form': VroomForm(),
                'shipments_html' : shipments_original.to_html(classes='table table-striped'),
                'vehicles_html' : vehicles_original.to_html(classes='table table-striped'),
                'unassigned_html' : unassigned.to_html(classes='table table-striped'),
                'route_htmls' : route_htmls,
                'route_csvs' : route_csvs,
                'summary_html' : summary_html,
                'resultFlg' : True,
                'script_html' : script_html,
                'google_script_html' : google_script_html,
                'error_msg' : '',
                }
    
    
            return render(request, 'vroom/index.html', params)
        except Exception as e:
            print(e)
            error_msg = '予期せぬエラーが発生しました。:' + str(e)
            params = {
                'form': VroomForm(),
                'resultFlg' : False,
                'error_msg' : error_msg,
                }
            return render(request, 'vroom/index.html', params)

def get_h_m_s(td):
    m, s = divmod(td.seconds, 60)
    return str(m) + '分' +  str(s) + '秒'

def get_h_m_s(td):
    m, s = divmod(td.seconds, 60)
    h, m = divmod(m, 60)
    return str(h) + '時' + str(m) + '分' +  str(s) + '秒'

def to_h_m_s(sec_):
    m, s = divmod(sec_, 60)
    h, m = divmod(m, 60)
    return str(h) + '時' + str(m) + '分' +  str(s) + '秒'