from django import forms

class VroomForm(forms.Form):
    shipments_file = forms.fields.FileField(
        label='荷物データ',
        required=False,
        widget=forms.widgets.FileInput
    )

    vehicles_file = forms.fields.FileField(
        label='車両データ',
        required=False,
        widget=forms.widgets.FileInput
    )
         
class HatakeForm(forms.Form):
    csv_file = forms.fields.FileField(
        label='CSVデータ',
        required=False,
        widget=forms.widgets.FileInput
    )

    yayoi_file = forms.fields.FileField(
        label='弥生データ',
        required=False,
        widget=forms.widgets.FileInput
    )

    intra_file = forms.fields.FileField(
        label='イントラマートデータ',
        required=False,
        widget=forms.widgets.FileInput
    )

    address_file = forms.fields.FileField(
        label='配送リスト',
        required=False,
        widget=forms.widgets.FileInput
    )

    CHOICE = [
        ('1','1'),
        ('2','2'),
        ('3','3'),
        ('4','4'),
        ('5','5'),
        ('6','6'),
        ('7','7'),
        ('8','8'),
        ('9','9'),
        ('10','10')]
        
    car_num = forms.ChoiceField(
        label='配送車の台数',
        required=True,
        disabled=False,
        initial=['5'],
        choices=CHOICE,
        widget=forms.Select(attrs={'id': 'one',}))

class VroomForm2(forms.Form):
    routes_file = forms.fields.FileField(
        label='経路データ',
        required=True,
        widget=forms.widgets.FileInput
    )
