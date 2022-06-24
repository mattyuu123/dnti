import pandas as pd
from django.shortcuts import render
from django.http import HttpResponse
from requests.api import request
from .forms import VroomForm
from .forms import VroomForm2
from .forms import VroomForm3
from django.views.generic import TemplateView
import requests
import json
from pandas.io.json import json_normalize
import random
import numpy as np
import math

START_LAT = 35.640861
START_LON = 139.8008
START_ADDRESS = '東京都中央区銀座2-2-14'
DELIVERY_TIME = 5*60

class VroomView3(TemplateView):
    def __init__(self):
        None

    def get(self, request):
        params = {
            'form': VroomForm(),
            'resultFlg' : False,
            'error_msg' : '',
            'calc_df' : '',
            }
        return render(request, 'vroom/hatake.html', params)


    def post(self, request):

        try:
            form = VroomForm(request.POST, request.FILES)
            shipments = pd.DataFrame(columns=['ID','会社名','配送先住所','配送先緯度','配送先経度','金額'])


            if form.is_valid():
                error_msg = ''
                csv_data = load_file('csv_file', request, ['ID','会社名','配送先住所','配送先緯度','配送先経度','金額'])
                yayoi_data = load_file('yayoi_file', request, ["得意先名","金額"])
                intra_data = load_file('intra_file', request, ["［取引先名］","［金額］"]).rename(columns={'［取引先名］': '得意先名','［金額］': '金額'})
                address_data = load_file('address_file', request, ['店舗名','住所1','緯度','経度'])
                
                shipment_data = pd.concat([yayoi_data, intra_data], axis=0)
                shipment_data = shipment_data.groupby('得意先名').sum().reset_index()
                shipments = pd.DataFrame(columns=['ID','会社名','配送先住所','配送先緯度','配送先経度','金額'],index=range(len(shipment_data)))
                for index, record in shipment_data.iterrows():   
                    shipments.iloc[index, shipments.columns.get_loc('会社名')] = record['得意先名']
                    try:
                        shipments.iloc[index, shipments.columns.get_loc('配送先住所')] = address_data[address_data['店舗名'] == record['得意先名']]['住所1'].iloc[0]
                        shipments.iloc[index, shipments.columns.get_loc('配送先緯度')] = address_data[address_data['店舗名'] == record['得意先名']]['緯度'].iloc[0]
                        shipments.iloc[index, shipments.columns.get_loc('配送先経度')] = address_data[address_data['店舗名'] == record['得意先名']]['経度'].iloc[0]
                    except:
                        print(record['得意先名'] + 'が住所リストに存在しません')
                        error_msg += record['得意先名'] + 'が住所リストに存在しません<br/>'
                    shipments.iloc[index, shipments.columns.get_loc('金額')] = record['金額']

                shipments = shipments.dropna(subset=['配送先住所'])
                shipments = pd.concat([csv_data, shipments], axis=0)
                shipments = shipments.reset_index(drop=True)
                shipments['ID'] = shipments.index

                if len(shipments) == 0:
                    error_msg += '対象データが0件です。'

                if error_msg != '':
                    params = {
                        'form': VroomForm(),
                        'error_msg' : error_msg,
                        'resultFlg' : False,
                        'calc_df' : '',
                        }
                    return render(request, 'vroom/hatake.html', params)
        except Exception as e:
            print(e)
            import traceback
            traceback.print_exc()
            error_msg = '入力ファイルが不正です。:' + str(e)
            params = {
                    'form': VroomForm(),
                    'resultFlg' : False,
                    'error_msg' : error_msg,
                    'merge_pd' : '',
                    'error_msg2' : '',
                    'calc_df' : ''
                    }
            return render(request, 'vroom/hatake.html', params)


        address_dict_d = {}
        if '配送先住所' in shipments.columns:
            for index, row in shipments.iterrows():
                address_dict_d[row['ID']] = row['配送先住所']

        company_name_dict = {}
        if '会社名' in shipments.columns:
            for index, row in shipments.iterrows():
                company_name_dict[row['ID']] = row['会社名']

        price_dict = {}
        if '金額' in shipments.columns:
            for index, row in shipments.iterrows():
                price_dict[row['ID']] = row['金額']

        car_num = int(request.POST['car_num'])
        input_json = make_input_json(shipments, car_num)
        
        end_times = []
        route_nums = []
        unassigned_nums = []
        success = False
        unassigned = ''

        once = False
        break_flg = False
        for end_time_h in [8,9,10,11,12]:
            for end_time_m in [0,10,20,30,40,50]:
                end_time = 3600*end_time_h + 60*end_time_m
                input_json_ = input_json.replace('__ENDTIME__', str(end_time) )
                print('-------------' + str(end_time))
                result_json = calc_route(input_json_)
                routes = result_json['routes']
                unassigned = result_json['unassigned']
                end_times.append(to_h_m(end_time))
                route_nums.append(len(routes))
                unassigned_nums.append(int(len(unassigned)/2))
                if len(routes) == car_num:
                    once = True
                if len(routes) == car_num and len(unassigned) == 0:
                    success = True
                    break_flg = True
                    break
                if once and len(routes) < car_num:
                    success = True
                    routes = before_routes
                    unassigned = before_unassigned
                    break_flg = True
                    break
                before_routes = result_json['routes']
                before_unassigned = result_json['unassigned']
            if break_flg:
                break

        calc_df = pd.DataFrame({
                        '締め時間' : end_times,
                        '配送車の数' : route_nums,
                        '未配達の数' : unassigned_nums })
        if not success:
            params = {
                'form': VroomForm(),
                'error_msg' : '最適な組合せが存在しませんでした。',
                'resultFlg' : False,
                'calc_df' : calc_df.to_html(classes='table table-striped', index=False)
                }
            print(calc_df)
            return render(request, 'vroom/hatake.html', params)

        script_html, google_script_html, route_htmls, route_csvs, summary_df, unassigned = make_htmls(routes, shipments, address_dict_d, company_name_dict, price_dict, unassigned)

        params = {
            'form': VroomForm(),
            'shipments_html' : shipments.head(10).to_html(classes='table table-striped'),
            'shipments_csv' : shipments.to_csv(index=False),
            'route_htmls' : route_htmls,
            'route_csvs' : route_csvs,
            'summary_df' : summary_df.to_html(classes='table table-striped', index=False),
            'unassigned' : unassigned.to_html(classes='table table-striped'),
            'resultFlg' : True,
            'script_html' : script_html,
            'google_script_html' : google_script_html,
            'error_msg' : '',
            'calc_df' : calc_df.to_html(classes='table table-striped', index=False)
            }


        return render(request, 'vroom/hatake.html', params)




def load_file(file_name, request, columns):
    if file_name in request.FILES:
        df = load_file_(request.FILES[file_name])
        df = df[columns]
    else:
        df = pd.DataFrame(columns=columns)

    return df

def load_file_(file_obj):
    try:
        df = pd.read_csv(file_obj , encoding= "SHIFT-JIS",thousands=',')
    except:
        try:
            df = pd.read_csv(file_obj , encoding= "UTF-8", thousands=',')
        except:
            df = pd.read_excel(file_obj)

    return df

def get_h_m_s(td):
    m, s = divmod(td.seconds, 60)
    return str(m) + '分' +  str(s) + '秒'

def get_h_m_s(td):
    m, s = divmod(td.seconds, 60)
    h, m = divmod(m, 60)
    return str(h) + '時' + str(m) + '分' +  str(s) + '秒'

def to_h_m(sec_):
    m, s = divmod(sec_, 60)
    h, m = divmod(m, 60)
    return str(h) + '時' + str(m) + '分'

def to_h_m_s(sec_):
    m, s = divmod(sec_, 60)
    h, m = divmod(m, 60)
    return str(h) + '時' + str(m) + '分' +  str(s) + '秒'

def get_angle_num(ido, keido, n):
    theta = math.atan2(ido,keido)+math.pi
    return int(np.floor(n*theta/(2*math.pi)))

def make_input_json(shipments, car_num):
    shipments['angle_num'] = 0
    shipments['distance'] = 0

    average_ido = shipments['配送先緯度'].mean()
    average_keido = shipments['配送先経度'].mean()
    
    for index, row in shipments.iterrows():
        shipments.loc[index,'distance'] = np.sqrt((shipments.loc[index,'配送先緯度']-average_ido)**2+(shipments.loc[index,'配送先経度']-average_keido)**2)
        shipments.loc[index,'angle_num'] = get_angle_num(shipments.loc[index,'配送先緯度']-average_ido,shipments.loc[index,'配送先経度']-average_keido,car_num)

    input_json = '{ "vehicles": ['
    for index in range(car_num):
        input_json += ' { '
        input_json += ' "id": {},'.format(str(index+1))
        input_json += ' "start": [ {} , {} ],'.format(START_LON,START_LAT)
        ship_a = shipments[shipments['angle_num'] == index]
        ship_max = ship_a.loc[[ship_a['distance'].idxmax()]]
        input_json += ' "end": [ {} , {} ],'.format(list(ship_max['配送先経度'])[0], list(ship_max['配送先緯度'])[0])
        input_json += ' "time_window": [ {} , __ENDTIME__ ]'.format(8*3600)  
        input_json += ' }'
        if index != car_num-1:
            input_json += ','

    input_json += ' ],'

    input_json += ' "shipments": ['
    for index, shipment in shipments.iterrows():
        input_json += ' { '
        input_json += ' "pickup": {{ "id": {} , "service": 0, "location": [ {} , {} ], "time_windows": [[ {}, {}]] }},'.format(int(shipment['ID']),START_LON,START_LAT,8*3600,23*3600)
        input_json += ' "delivery": {{ "id": {} , "service": 300, "location": [ {} , {} ], "time_windows": [[ {}, {}]] }}'.format(int(shipment['ID']),shipment['配送先経度'],shipment['配送先緯度'],8*3600,23*3600)
        input_json += ' }'
        
        if index != len(shipments)-1:
            input_json += ','

    input_json += ']}'

    shipments.drop(columns=['angle_num', 'distance'], inplace=True)

    return input_json


def calc_route(input_json):
    headers = {
        'Content-type': 'application/json',
        }
        
    response = requests.post('http://10.0.2.20:5000/', headers=headers, data=input_json)    
    result = response._content.decode()
    result_json = json.loads(result)

    return result_json


def make_htmls(routes, shipments, address_dict_d, company_name_dict, price_dict, unassigned):
    summary_car_index = []
    summary_price = []
    summary_time = []
    summary_shipments_num = []
    
    route_htmls = []
    route_csvs = []

    if len(unassigned) > 0:
        unassigned = json_normalize(unassigned).sort_values(by=['id','type'],ascending=[True,False]).reset_index().drop('index', axis=1)
    else:
        unassigned = pd.DataFrame(unassigned)

    unassigned['配送先住所'] = ''
    unassigned['会社名'] = ''
    unassigned['金額'] = ''
    if '配送先住所' in shipments.columns:
        for index, row in unassigned.iterrows():
            if row['type'] == 'delivery':
                unassigned.loc[index,'配送先住所'] = address_dict_d[int(row['id'])]

    if '会社名' in shipments.columns:
        for index, row in unassigned.iterrows():
            if not np.isnan(row['id']):
                unassigned.loc[index,'会社名'] = company_name_dict[int(row['id'])]

    if '金額' in shipments.columns:
        for index, row in unassigned.iterrows():
            if not np.isnan(row['id']):
                unassigned.loc[index,'price'] = price_dict[int(row['id'])]

    if len(unassigned) > 0:
        unassigned = unassigned[unassigned['type'] == 'delivery'][['id','配送先住所','会社名','金額']]
    else:
        unassigned = pd.DataFrame(columns=['id','配送先住所','会社名','金額'])

    script_html = '<script>function initMap() {'
    colors = ['#ff0000','#ff007f','#ff00ff','#7f00ff','#0000ff','#007fff','#00ffff','#00ff7f','#00ff00','#7fff00','#ff7f00']
    for car_index, route in enumerate(routes):
        total_price = 0
        map_html = '<div id="map' + str(route["vehicle"]) + '" style="width:800px; height:800px"></div>'
        df_steps = json_normalize(route['steps'])
        df_steps['time'] = df_steps['arrival'].map(to_h_m_s)
        df_steps['address'] = ''
        df_steps['company'] = ''
        df_steps['price'] = ''
        if '配送先住所' in shipments.columns:
            for index, row in df_steps.iterrows():
                if row['type'] == 'pickup':
                    df_steps.loc[index,'address'] = START_ADDRESS
                elif row['type'] == 'delivery':
                    df_steps.loc[index,'address'] = address_dict_d[int(row['id'])]

        if '会社名' in shipments.columns:
            for index, row in df_steps.iterrows():
                if not np.isnan(row['id']):
                    df_steps.loc[index,'company'] = company_name_dict[int(row['id'])]

        if '金額' in shipments.columns:
            for index, row in df_steps.iterrows():
                if not np.isnan(row['id']) and row['type'] == 'delivery':
                    total_price += price_dict[int(row['id'])]
                    df_steps.loc[index,'price'] = price_dict[int(row['id'])]
        vehicle_df = json_normalize(route).drop('steps', axis=1)
        vehicle_df['total_price'] = int(total_price)


        summary_car_index.append(car_index + 1)
        summary_price.append(total_price)
        summary_time.append(list(df_steps['time'])[-1])
        summary_shipments_num.append(int((len(df_steps)-2)/2))

        df_steps = df_steps[df_steps['type'] == 'delivery']


        route_htmls.append((route['vehicle'], vehicle_df.to_html(index = False, classes='table table-striped'), df_steps[['type','id','time','address','company','price']].to_html(classes='table table-striped'),map_html))
        route_csvs.append(df_steps[['type','id','time','address','company','price']].to_csv(index = False))
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
            script_html += '        { lat:"' + str(step['location'][1]) + '", lng:"' + str(step['location'][0]) + '", title:"type:' + step['type'] + ','  + 'arrival:' + to_h_m_s(step['arrival']) + ',' + 'service:' + to_h_m_s(step['service']) + ',' + 'duration:' + str(step['duration'])  + '" },'
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
    summary_df = pd.DataFrame({
                    '配送車No' : summary_car_index,
                    '合計金額' : summary_price,
                    '終了時刻' : summary_time,
                    '配達数' : summary_shipments_num })

    return script_html, google_script_html, route_htmls, route_csvs, summary_df, unassigned