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


class VroomView2(TemplateView):
    def __init__(self):
        None

    def get(self, request):
        params = {
            'form': VroomForm2(),
            'resultFlg' : False,
            'error_msg' : '',
            }
        return render(request, 'vroom/index2.html', params)

    def post(self, request):

        try:
            form = VroomForm2(request.POST, request.FILES)
            if form.is_valid():
                try:
                    routes_file = request.FILES['routes_file']
    
                    routes = pd.read_csv(routes_file).sort_values(["配車","順番"])

                    memo_dict = {}
                    for index, row in routes.iterrows():
                        memo_dict[str(row['配車']) + '_' + str(row['順番'])] = row['メモ']

                    routes_original = routes
                except ModuleNotFoundError as e:
                    print(e)
                    error_msg = 'CSVファイルが不正です。:' + str(e)
                    params = {
                        'form': VroomForm2(),
                        'resultFlg' : False,
                        'error_msg' : error_msg,
                        }
                    return render(request, 'vroom/index2.html', params)

            routes_dict = {}
            for i in routes['配車'].unique():
                routes_dict[i]=routes[routes['配車']==i]

            route_htmls = []
            route_csvs = []
            script_html = '<script>function initMap() {'
            colors = ['#ff0000','#ff007f','#ff00ff','#7f00ff','#0000ff','#007fff','#00ffff','#00ff7f','#00ff00','#7fff00','#ff7f00']
            for index, route in routes_dict.items():
                map_html = '<div id="map' + str(index) + '" style="width:800px; height:800px"></div>'

                route_htmls.append((index, route.to_html(index = False, classes='table table-striped'),map_html))
                script_html += 'var opts' + str(index) + ' = {zoom: 13,center: new google.maps.LatLng(' + str(route.iloc[0]['緯度']) + ',' +  str(route.iloc[0]['経度']) + ')};'
                script_html += 'var map' + str(index) + '  = new google.maps.Map(document.getElementById("map' + str(index) + '"), opts' + str(index) + ' );'
                script_html += 'var flightPlanCoordinates' + str(index) + ' = [ '
                for index2, step in route.iterrows():
                    script_html += 'new google.maps.LatLng(' + str(step['緯度']) + ',' +  str(step['経度']) + '),'
                script_html += '];'
                script_html += 'var flightPath' + str(index) + ' = new google.maps.Polyline({path: flightPlanCoordinates' + str(index) + ','
                script_html += 'strokeColor: "' + colors[random.randint(0,len(colors)-1)] + '", strokeOpacity: 1.0, strokeWeight: 5 });'
                script_html += 'flightPath' + str(index) + '.setMap(map' + str(index)  + ' );'
                script_html += '    var markerData' + str(index) + ' = ['
                for index3, step in route.iterrows():
                    script_html += '        { lat:"' + str(step['緯度']) + '", lng:"' + str(step['経度']) + '" },'
                script_html += '    ];'
                script_html += '    for (i = 0;i < markerData' + str(index) + '.length;i++) {'
                script_html += '        var marker = new google.maps.Marker({'
                script_html += '            position: new google.maps.LatLng(markerData' + str(index) + '[i].lat, markerData' + str(index) + '[i].lng),'
                script_html += '            icon: {  fillColor: "#FF00FF",  fillOpacity: 0.8,  path: google.maps.SymbolPath.CIRCLE,  scale: 16,  strokeColor: "#FF0000",  strokeWeight: 1.0 }, label: {  text:  String(i+1)  ,  color: "#FFFFFF",  fontSize: "20px" },'
                script_html += '            title: markerData' + str(index) + '[i].title'
                script_html += '        });'

                script_html += '        marker.setMap(map' + str(index)  + ');'
                script_html += '    }'
            script_html += '}</script>'

            google_script_html = '<script async defer  src="https://maps.googleapis.com/maps/api/js?key=AIzaSyAbBWy9eBi2VI1j5nC82yPN1I7hBMu9fvk&callback=initMap"></script>'
    
            print(script_html)

            params = {
                'form': VroomForm2(),
                'route_htmls' : route_htmls,
                'resultFlg' : True,
                'script_html' : script_html,
                'google_script_html' : google_script_html,
                'error_msg' : '',
                }
    
    
            return render(request, 'vroom/index2.html', params)
        except ModuleNotFoundError as e:
            print('error')
            pass
            # print('hoga')
            # print(e)
            # error_msg = '予期せぬエラーが発生しました。:' + str(e)
            # params = {
            #     'form': VroomForm2(),
            #     'resultFlg' : False,
            #     'error_msg' : error_msg,
            #     }
            # return render(request, 'vroom/index2.html', params)

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